# Cases

Eight firmware failures that happened, with a public record. Each one is the test: given
only the failure description, does the sheet point at the decision that would have
prevented it?

Every case names the rule it tests and the source it came from. Sources were read on
2026-11-17. Where a case rests on contested expert testimony rather than a regulator
finding, it says so.


## C1. Mars Pathfinder, July 1997. Priority inversion.

The lander reset repeatedly on the surface. A high-priority bus distribution task was
blocked on a mutex held by a much lower-priority meteorological task, while medium-priority
tasks kept running. The fix uploaded to Mars changed the semaphore creation flags to
enable priority inheritance.

Tests rule 7. Status: documented, primary source.
Source: Glenn E. Reeves (JPL, Pathfinder flight software lead), "What really happened on
Mars", public email, 1997; and "Priority Inversion: How We Found It, How We Fixed It",
Dr. Dobb's Journal, November 1999.

## C2. Boeing 787 generator control units, FAA directive 2015. Counter overflow.

A software counter inside each generator control unit overflowed after 248 days of
continuous power. Four units powered up together would enter failsafe at the same moment
and drop all AC electrical power in any phase of flight. The interim remedy was a
scheduled power cycle; the permanent one was new GCU software three years later.

Note the arithmetic: 248.55 days is 2^31 at a 10 ms tick. The unit sets the date, the wrap
is certain either way.

Tests rule 9. Status: documented, regulator finding.
Source: FAA Airworthiness Directive 2015-09-07, issued as a final rule effective
immediately, superseded by AD 2018-20-15 which mandates the new GCU software.

## C3. Ariane 5 flight 501, June 1996. The error path was the failure.

A 64-bit float to 16-bit signed integer conversion in the inertial reference system
overflowed and raised an Operand Error. The conversion was unguarded, while comparable
conversions nearby were guarded. The board was explicit that the operand error alone did
not lose the mission: the exception handling did. The unit shut down and put a diagnostic
bit pattern on the bus, which the on-board computer read as flight data.

Tests rules 3 and 15. Status: documented, primary source.
Source: Ariane 501 Inquiry Board report, ESA and CNES, presented 23 July 1996.

## C4. Toyota electronic throttle, Bookout trial, October 2013. Stack headroom.

Expert testimony in a jury trial put measured stack usage at 94% where Toyota had reported
41% to NASA, found recursion in the code, no memory protection unit guarding the stack,
and no run-time stack monitoring.

Tests rule 11. Status: contested. This is plaintiff expert testimony, disputed by Toyota,
not a regulator finding. It is in the corpus because the dispute is precisely about
measurement versus a reported figure, which is what the rule asks for.
Source: Michael Barr, expert testimony and slides, Bookout v. Toyota, Oklahoma, October
2013.

## C5. Tesla Model S and X media control unit, NHTSA recall 2021. Flash wear.

The 8 GB eMMC in the media control unit is rated for roughly 3,000 program/erase cycles.
Routine logging consumed them. Tesla confirmed to the regulator that every affected unit
would inevitably fail, and the remedy was replacing the hardware.

Tests rule 19, which asks for the erase-cycle figure of the part and a write budget
measured against it. The figure existed; nothing was budgeted against it.

Tests rule 19. Status: documented, regulator finding.
Source: NHTSA Part 573 safety recall report 21V-035, submitted 29 January 2021, following
investigation EA20003.

## C6. LockState smart locks, 8 August 2017. Image for the wrong hardware revision.

An over-the-air update built for one model was pushed to a different model. At least 500
locks stopped working, could not be recovered remotely, and had to be shipped back for a
manual reset. Guests kept out; hosts handed out physical keys.

Tests rule 25 first, because a canary on real devices of every hardware revision is what
catches an image aimed at the wrong model. Also rule 22: with A/B partitions and a
required health confirmation, a wrong image reverts instead of bricking.

Tests rules 25 and 22. Status: documented, company statement plus contemporary reporting.
Source: LockState letter to customers, August 2017, as reported by BleepingComputer,
TechSpot and Graham Cluley, 13-14 August 2017.

## C7. Nest thermostat firmware 5.1.3, January 2016. It booted, and then it died.

An update shipped in December drained the battery and left units unresponsive and the
heating off, in winter. By the company's account the symptom did not appear for about two
weeks on most affected units. Recovery required unplugging the device and charging it over
USB by hand.

This case is in the corpus because the sheet only partly catches it. A health
confirmation window (rule 22) measured in seconds or minutes sees a healthy device: the
failure takes two weeks to surface. What catches it is a staged rollout gated on
post-update check-ins over time (rule 25) and field health telemetry. A sheet that claimed
this one as a clean hit would be lying.

Tests rule 25, and marks the limit of rule 22. Status: documented, company statement plus
contemporary reporting.
Source: Nest statements as reported by The Register and 9to5Google, 14 January 2016.

## C8. ESP-IDF bootloader, CVE-2024-28183. Signed, old, and accepted.

A time-of-check to time-of-use flaw let an attacker with physical access bypass the
anti-rollback check and install an older image. Anti-rollback in that platform is a
separate build option backed by an eFuse security version; signature verification alone
never prevented a downgrade.

Tests rule 24. Status: documented, assigned CVE with a published write-up.
Source: CVE-2024-28183; elttam public write-up, 2024.


## Rules with no case in this corpus

Rule 8, every wait on hardware bounded by a timeout, and rule 20, power-fail-safe
non-volatile writes, have no case here. Both are in the sheet on the strength of
engineering practice, not on a failure this corpus can cite. They carry their confidence
on that basis, and a documented case for either is the most useful contribution this
repository can receive.
