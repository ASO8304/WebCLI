"""
tcpdump_runner.py

Secure runner that launches tcpdump via the approved root wrapper:
    /usr/local/sbin/webcli-tcpdump.sh

Behaviour & security notes:
 - We do conservative client-side validation of tokens to avoid obvious misuse.
 - We disallow suspicious shell metacharacters in tokens.
 - We limit number of tokens and token lengths.
 - We special-case "-w" (write capture) to restrict output files to /var/log/webcli
   (if caller passes a basename we map it to /var/log/webcli/<basename>.pcap).
 - We allow "-Z" to specify drop-user but validate username format; wrapper still enforces.
 - We never use shell=True; we always exec with an argument list.
 - Final validation/enforcement must still be done by the root wrapper.
"""

from __future__ import annotations

import asyncio
import os
import re
import shlex
import logging
from logging.handlers import RotatingFileHandler
from typing import List, Optional

from core.process_manager import (
    set_current_process,
    clear_current_process,
    get_current_process,
)

# ------- Configuration -------
WRAPPER_PATH = "/usr/local/sbin/webcli-tcpdump.sh"   # must match sudoers
SUDO = "sudo"
LOG_DIR = "/var/log/webcli"
LOG_FILE = os.path.join(LOG_DIR, "tcpdump_runner.log")
MAX_TOKENS = 80
MAX_TOKEN_LEN = 256
MAX_CMD_CHARS = 4096

# Allowed tokens & keywords (client-side whitelist)
ALLOWED_FLAGS = {
    "-i", "-n", "-nn", "-v", "-vv", "-vvv", "-c", "-s", "-X", "-XX",
    "-A", "-e", "-tt", "-ttt", "-q", "-Q", "-U", "-E", "-p", "-Z",
}
FLAGS_WITH_ARG = {"-i", "-c", "-s", "-w", "-r", "-E", "-Q", "-Z"}
ALLOWED_KEYWORDS = {
    "port", "host", "src", "dst", "and", "or", "not", "ip", "ip6", "tcp", "udp", "icmp"
}

# Safe patterns
RE_SAFE_TOKEN = re.compile(r"^[A-Za-z0-9._:@\-/]+$")   # conservative: allow dots, underscores, at, colon, -, / (slash only in paths)
RE_IFACE = re.compile(r"^[A-Za-z0-9._:-]+$")
RE_USERNAME = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")  # typical linux username rules
RE_IPV4 = re.compile(r"^([0-9]{1,3}\.){3}[0-9]{1,3}$")
RE_NUMBER = re.compile(r"^[0-9]+$")

# Allowed base directory for -w write outputs (prevent writing everywhere)
ALLOWED_WRITE_DIR = "/var/log/webcli"
ALLOWED_WRITE_BASENAME = re.compile(r"^[A-Za-z0-9._-]{1,200}$")

# Ensure log dir exists and configure logging
if not os.path.isdir(LOG_DIR):
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
    except Exception:
        pass

logger = logging.getLogger("webcli.tcpdump_runner")
logger.setLevel(logging.INFO)
if os.path.isdir(LOG_DIR):
    fh = RotatingFileHandler(LOG_FILE, maxBytes=5_000_000, backupCount=3)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
    logger.addHandler(fh)
else:
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
    logger.addHandler(sh)


# ------- Helpers & Validation -------

class ValidationError(Exception):
    pass


def _reject_suspicious_token(tok: str) -> None:
    if len(tok) > MAX_TOKEN_LEN:
        raise ValidationError(f"token too long: {tok!r}")
    if re.search(r"[;&|`$<>*?\(\)\{\}\[\]]", tok):
        raise ValidationError(f"suspicious token contains shell metacharacter: {tok!r}")
    if not RE_SAFE_TOKEN.match(tok):
        raise ValidationError(f"token contains unsafe characters: {tok!r}")


def _validate_and_normalize_tokens(tokens: List[str]) -> List[str]:
    if len(tokens) == 0:
        raise ValidationError("no tcpdump arguments provided")
    if len(tokens) > MAX_TOKENS:
        raise ValidationError("too many arguments")
    cmdchars = sum(len(t) for t in tokens) + len(tokens) - 1
    if cmdchars > MAX_CMD_CHARS:
        raise ValidationError("command too long")

    out_tokens: List[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        _reject_suspicious_token(tok)

        if tok in ALLOWED_FLAGS:
            out_tokens.append(tok)
            if tok in FLAGS_WITH_ARG:
                if i + 1 >= len(tokens):
                    raise ValidationError(f"flag {tok} requires an argument")
                param = tokens[i + 1]
                _reject_suspicious_token(param)

                if tok == "-i":
                    if not RE_IFACE.match(param):
                        raise ValidationError(f"invalid interface: {param!r}")
                    out_tokens.append(param)
                    i += 2
                    continue

                if tok == "-Z":
                    if not RE_USERNAME.match(param):
                        raise ValidationError(f"invalid username for -Z: {param!r}")
                    out_tokens.append(param)
                    i += 2
                    continue

                if tok == "-w":
                    if param.startswith("/"):
                        norm_path = os.path.normpath(param)
                        if not norm_path.startswith(ALLOWED_WRITE_DIR + "/") and norm_path != ALLOWED_WRITE_DIR:
                            raise ValidationError(f"-w output path must be under {ALLOWED_WRITE_DIR}: {param!r}")
                        out_tokens.append(norm_path)
                        i += 2
                        continue
                    else:
                        if not ALLOWED_WRITE_BASENAME.match(param):
                            raise ValidationError(f"invalid -w filename: {param!r}")
                        mapped = os.path.join(ALLOWED_WRITE_DIR, param)
                        out_tokens.append(mapped)
                        i += 2
                        continue

                if tok in {"-c", "-s"}:
                    if not RE_NUMBER.match(param):
                        raise ValidationError(f"argument for {tok} must be numeric: {param!r}")
                    out_tokens.append(param)
                    i += 2
                    continue

                if tok == "-r":
                    raise ValidationError("-r (read capture) not allowed via web interface")

                if param.startswith("-"):
                    raise ValidationError(f"invalid argument after {tok}: {param!r}")
                out_tokens.append(param)
                i += 2
                continue
            i += 1
            continue

        if tok in ALLOWED_KEYWORDS or RE_NUMBER.match(tok) or RE_IPV4.match(tok):
            out_tokens.append(tok)
            i += 1
            continue

        if re.match(r"^[A-Za-z0-9\.-]{1,128}$", tok):
            out_tokens.append(tok)
            i += 1
            continue

        raise ValidationError(f"unsupported or unsafe token: {tok!r}")

    if "-w" in out_tokens and not os.path.isdir(ALLOWED_WRITE_DIR):
        try:
            os.makedirs(ALLOWED_WRITE_DIR, exist_ok=True)
            logger.info("created allowed write dir %s", ALLOWED_WRITE_DIR)
        except Exception as e:
            raise ValidationError(f"cannot prepare write directory {ALLOWED_WRITE_DIR}: {e}")

    z_count = sum(1 for t in out_tokens if t == "-Z")
    if z_count > 1:
        raise ValidationError("multiple -Z flags not allowed")

    return out_tokens

# ------- Runner API (async) -------
async def handle_tcpdump(websocket, cmd: str):
    if not os.path.isfile(WRAPPER_PATH):
        await websocket.send_text("❌ tcpdump wrapper not available or not executable.")
        logger.error("wrapper missing or not executable: %s", WRAPPER_PATH)
        return

    try:
        parts = shlex.split(cmd.strip())
    except ValueError as e:
        await websocket.send_text(f"❌ Failed to parse command: {e}")
        return

    if len(parts) == 0 or parts[0] != "tcpdump":
        await websocket.send_text("❌ Only 'tcpdump' commands are supported.")
        return

    tokens = parts[1:]
    try:
        validated = _validate_and_normalize_tokens(tokens)
    except Exception as ve:
        await websocket.send_text(f"❌ Invalid tcpdump arguments: {ve}")
        return

    full_cmd = [SUDO, WRAPPER_PATH] + validated
    await websocket.send_text(
        f"🐾 Running tcpdump via wrapper: {' '.join(full_cmd)}\n(collecting packets...)\n"
    )

    process = await asyncio.create_subprocess_exec(
        *full_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    # store both process and current task in process_manager
    set_current_process(websocket, process, asyncio.current_task())

    # Reader task to stream stdout
    async def reader_task_fn():
        try:
            assert process.stdout is not None
            async for raw_line in process.stdout:
                line = raw_line.decode(errors="ignore").rstrip()
                if len(line) > 2000:
                    line = line[:2000] + "…[truncated]"
                await websocket.send_text(line)
        except asyncio.CancelledError:
            # Reader cancelled on interrupt
            return

    reader_task = asyncio.create_task(reader_task_fn())

    try:
        await process.wait()
        await reader_task
        await websocket.send_text(f"\n✅ tcpdump finished (exit code {process.returncode})")
    except asyncio.CancelledError:
        # Ctrl+C: terminate/kill process and cancel reader
        proc = get_current_process(websocket)
        if proc and proc.returncode is None:
            try:
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=3.0)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
            except Exception:
                logger.exception("failed to terminate tcpdump")
        reader_task.cancel()
        await websocket.send_text("\n⚠️ tcpdump interrupted by user (Ctrl+C).")
        raise  # re-raise so admin_handler’s done_callback runs
    except Exception as e:
        logger.exception("tcpdump runner error: %s", e)
        await websocket.send_text(f"\n⚠️ tcpdump terminated with error: {e}")
    finally:
        clear_current_process(websocket)

