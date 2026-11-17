# truckroll

Thirty-one decisions that decide whether embedded firmware survives the field.

Each rule carries a scope and a confidence. The scope says where it applies: `any`,
`RTOS`, `OTA` for a device that updates itself in the field, `fleet` for devices nobody
can physically reach. The confidence says how sure the rule is of itself, not how bad the
failure is. A 0.95 is a law. A 0.75 is a rule reasonable engineers disagree about, and you
should turn it off on purpose if you disagree.

Confidence here is not a vote, and it is not a measurement either. It is a judgement, put
under a test that can embarrass it.

The test is knockout against the documented failures in [CASES.md](CASES.md): drop a rule,
ask again, and see whether the failure is still diagnosed without it. The results are in
[SCORES.md](SCORES.md), including the rules that turned out not to carry the answer they
claim to carry.

What the numbers here do not do is move on thin evidence. This corpus has one case per
rule and a handful of judges, so a rule that looks dispensable in a single knockout is a
rule with one data point against it, not a refuted rule. Swinging a confidence from 0.95
to 0.80 on that would be the same false rigour this repository was built to avoid. A
number moves when the signal is unambiguous across every judge, and the knockout result
sits next to the rule either way, so you can disagree with the call.

## What the knockout found

Two judges, every rule in the corpus dropped once. No confidence moved, and the reason is
the policy above rather than a shortage of nerve.

Rules 19 and 24 came out load-bearing for both judges: cut either one and the failure it
covers stops being diagnosed. Rules 3 and 9 were load-bearing for one judge and dispensable
for the other, which is one data point each way.

Rules 7, 11 and 25 produced no signal at all, and that result is about the writing, not the
engineering. The sheet misses those three cases even with the rule sitting right there in
front of the reader: nobody gets from "resets in the field, never on the bench" to priority
inheritance, from "comfortable margins in the design document" to measuring the stack, or
from "a subset sharing a manufacturing date" to canarying per hardware revision. The rules
are right and the path from symptom to rule is missing. Fixing that is the next piece of
work on this file, and until it is done those three are worth less in practice than their
confidence suggests.

## Structure and host testing

1. `any` Keep hardware access behind a thin hardware abstraction layer so application logic can be built and unit-tested on the host machine. Confidence: 0.90.
2. `any` Run unit tests on the host in CI with Unity or GoogleTest, and keep on-target tests for drivers and timing only. Confidence: 0.85.
3. `any` Check the return value of every HAL, SDK and peripheral call, and give the error a path to the fault record. A driver that ignores a failed transfer reports healthy while the device is deaf. Confidence: 0.95.

## Concurrency and timing

4. `any` Use a small RTOS such as Zephyr or FreeRTOS once there are more than two independent timing concerns, instead of growing a hand-written super loop. Confidence: 0.75.
5. `any` Keep interrupt handlers short: capture the data, set a flag or push to a queue, and do the real work in a task. Confidence: 0.95.
6. `any` Use `volatile` on data shared with an interrupt for visibility, and protect read-modify-write, misaligned, 64-bit and multi-word access with a critical section or C11 atomics. An aligned 32-bit load is already single-copy atomic on ARMv7-M; `volatile` alone never makes `flags |= BIT` safe. Confidence: 0.95.
7. `RTOS` Guard a shared resource with a mutex that carries priority inheritance, not a binary semaphore, and write down why each task priority is the number it is. Confidence: 0.90.
8. `any` Bound every wait on hardware with a timeout, and never block forever on a peripheral flag or on a queue that only a hardware event can fill. Confidence: 0.95.
9. `any` Compare deadlines with unsigned subtraction, `(now - start) >= timeout`, and assume the counter wraps: 32-bit milliseconds roll over in 49.7 days. Confidence: 0.95.

## Memory and stack

10. `any` Avoid dynamic memory allocation after startup; allocate buffers statically or from fixed-size pools sized at compile time. Confidence: 0.90.
11. `RTOS` Size every task stack from measurement, not a guess: turn on the kernel's stack-overflow check, read the high-water mark after the worst-case path rather than after an idle run, and keep headroom. Confidence: 0.90.
12. `any` Use fixed-width integer types like `uint32_t` everywhere hardware registers, protocols or storage formats are involved, and never lay a bitfield over a hardware register. Confidence: 0.90.
13. `any` Track flash and RAM usage per build in CI and fail when either crosses an agreed budget. Confidence: 0.80.

## Watchdog, faults and recovery

14. `any` Enable the hardware watchdog in production builds and feed it only from a health check that confirms every critical task is alive. Confidence: 0.90.
15. `any` Make the fault handler record and reset: store the program counter, fault registers and reset reason in retained RAM, reboot, and report the record on the next boot. A production handler that spins in `while (1)` turns a recoverable fault into a dead unit. Confidence: 0.90.

## Build and toolchain

16. `any` Build with `-Wall -Wextra -Werror` and run a static analyzer such as cppcheck or clang-tidy on every pull request. Confidence: 0.85.
17. `any` Pin the exact cross-compiler version and every library version in a container image, toolchain file or manifest, so a build from last year's tag still produces last year's binary. Confidence: 0.90.
18. `any` Embed the git commit hash and build time in every image and expose them through a version command or register. Confidence: 0.85.

## Storage and configuration

19. `any` Write wear-aware storage code: know the erase-cycle figure of the part, budget writes per day against it, batch writes, and use a flash file system such as littlefs, which is designed around power loss rather than only around wear. Confidence: 0.85.
20. `any` Assume the supply can drop in the middle of a write: make every non-volatile update transactional, writing the new copy and verifying it before a pointer or sequence number switches over, and enable the brown-out detector so the part stops writing before the rail leaves spec. Confidence: 0.90.
21. `any` Version configuration stored in flash and migrate it on boot, rather than assuming the layout never changes. Confidence: 0.80.

## Update, identity and protocol

22. `OTA` Ship updates with an A/B partition scheme and signed images, and require the new image to confirm its own health inside a watchdog window or the bootloader reverts. Failing to boot is the easy case; booting into an image that runs and is broken is the one that costs the fleet. Confidence: 0.95.
23. `OTA` Verify firmware signatures in the bootloader with a key the application cannot overwrite. Confidence: 0.95.
24. `OTA` Refuse an image whose version counter is below the one already on the device. A signed old image is still a signed vulnerable image. Confidence: 0.90.
25. `fleet` Never update the whole fleet at once: canary on real devices of every hardware revision, then phase the rollout, each stage gated on post-update healthy check-ins. Confidence: 0.90.
26. `fleet` Give every device a unique, revocable identity, generated on the device and held where the private key cannot be read back out, never a credential shared across the fleet. Confidence: 0.85.
27. `fleet` Version every wire format and keep last year's version decodable. The firmware shipped a year ago is still out there and may never be updated. Confidence: 0.85.
28. `any` Lock debug ports such as JTAG and SWD on production units, with a documented process for authorized recovery. Confidence: 0.85.

## Power

29. `any` Design for low power from the start: sleep by default, wake on interrupts, and measure current draw with real hardware. Confidence: 0.75.

## Release

30. `any` Use structured, compact logging with log levels and a ring buffer, and never call `printf` in interrupt context. Confidence: 0.85.
31. `any` Run a hardware-in-the-loop test rig in CI for the main boards before releasing a firmware version. Confidence: 0.70.
