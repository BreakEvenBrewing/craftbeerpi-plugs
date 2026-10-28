# cbpi4-sequent

A [CraftBeerPi4](https://openbrewing.gitbook.io/craftbeerpi4_support/) plugin
that exposes [Sequent Microsystems](https://sequentmicrosystems.com/) I2C
HATs as native CBPi sensor/actor types:

- **SequentRTD** — a temperature sensor reading a PT100 (or PT1000) probe
  from a [RTD Data Acquisition HAT](https://sequentmicrosystems.com/products/raspberry-pi-rtd-data-acquisition-card).
- **SequentRelay** — an on/off actor driving one relay on an
  [8-relay Industrial HAT](https://sequentmicrosystems.com/products/8-relays-stackable-card-for-raspberry-pi).

This plugin only provides hardware interfaces. It knows nothing about
kettles, mash steps, pumps, PID logic, or any other brewing concepts — all
of that orchestration stays in CraftBeerPi itself, where you configure
sensors and actors like any other CBPi component.

## How it talks to the hardware

The plugin uses Sequent's official Python libraries directly (no shelling
out to the `rtd`/`8relind` CLI tools):

- [`SMrtd`](https://pypi.org/project/SMrtd/) (`import librtd`) for the RTD HAT
- [`SM8relind`](https://pypi.org/project/SM8relind/) (`import lib8relind`) for the relay HAT

Hardware access is isolated behind two small adapter classes in
[`cbpi4_sequent/hardware.py`](cbpi4_sequent/hardware.py) — `RtdBoard` and
`RelayBoard` — so the CBPi sensor/actor classes never import the vendor
libraries directly, and so tests can substitute fakes instead of talking to
real I2C hardware.

## Prerequisites

- I2C enabled on the Raspberry Pi (`sudo raspi-config` → Interface Options → I2C)
- The Sequent boards detected and working via their vendor CLI tools
  (`rtd -list`, `8relind -list`) — this plugin assumes the hardware is
  already known-good
- **PT100 vs PT1000 is a board-level firmware setting**, not something this
  plugin configures. Set it once via the vendor CLI before using
  `SequentRTD`:

  ```bash
  # 0 = PT100, 1 = PT1000 — set on every RTD board you use
  rtd <board-id> stypewr 0
  ```

  If readings look wrong after a power cycle, re-check this setting — it's
  worth confirming it survives a reboot on your firmware revision.

## Installation

Install into the same Python environment CBPi itself runs in (the pipx venv
CBPi was installed into):

```bash
pipx runpip cbpi4 install cbpi4-sequent
```

Or, if installing from a local checkout of this repo:

```bash
pipx runpip cbpi4 install ./cbpi4-sequent
```

Then restart CBPi:

```bash
sudo systemctl restart craftbeerpi
```

`SequentRTD` and `SequentRelay` should now show up as available sensor and
actor types in the CBPi UI.

## Configuration

Both components take a **Board ID** (the stack address, selectable via the
board's address jumpers, 0-7) and a **channel**:

- `SequentRTD`: Board ID + RTD Channel (1-8) + read Interval (seconds),
  plus optional Calibration Offset / Calibration Unit (see below)
- `SequentRelay`: Board ID + Relay (1-8)

Add a sensor or actor from the CBPi UI, pick `SequentRTD` / `SequentRelay`
as the type, and fill in Board ID and channel to match your wiring — e.g.
Board ID 0, Relay 1 for the first relay on your only relay HAT.

### RTD calibration

Each `SequentRTD` can correct a probe's systematic error with two
properties:

- **CalibrationOffset** — degrees added to every successful reading.
  Positive, negative and fractional values are allowed. Default `0`
  (no correction); sensors configured before this option existed behave
  exactly as before.
- **CalibrationUnit** — `C` or `F`, the unit the offset is written in.
  Required whenever the offset is not 0; the sensor refuses to start
  (with an error in the CBPi UI/log) rather than guess.

The HAT always measures in °C. The plugin converts that to CBPi's
`TEMP_UNIT`, then adds the offset — converted to `TEMP_UNIT` as a
temperature *difference* (×9/5 or ×5/9, no ±32) if the units differ — and
rounds to 0.01°. That single corrected value is what the dashboard,
controllers/PID, recipes and CSV logs all receive. Switching `TEMP_UNIT`
later therefore keeps the correction physically the same size.

To calibrate, put the probes in the same well-stirred water bath (ideally
next to a trusted reference thermometer) and set
`offset = reference − reading`. For example, if the reference reads
92.7 °F and the probe reads 91.5 °F, set CalibrationOffset `1.2`,
CalibrationUnit `F`.

The offset is purely a software correction: it never touches the HAT's
own calibration or its raw measurements, and it is applied only after a
reading has succeeded. Failed reads and open/disconnected channels are
still detected on the raw value and logged, and no corrected value is
published for them.

## Error handling

If a board isn't detected, an RTD channel is open/disconnected, or an I2C
read/write otherwise fails, the adapters raise a `HardwareError`, which the
sensor/actor classes catch, log (`logging.getLogger("cbpi4_sequent...")`),
and recover from on the next poll/command rather than crashing the CBPi
process.

## Development / running tests

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pip install -e .
pytest
```

Tests mock both the Sequent vendor libraries and the minimal `cbpi.api`
surface this plugin uses, so the full test suite runs without any physical
hardware or a real CraftBeerPi installation.

## Scope

This plugin intentionally does **only** hardware I/O for these two boards.
It does not include Brewfather integration, PID logic, fermentation
control, or any brewery-specific behavior — that belongs in CBPi's own
configuration, kettle/fermenter logic, and other plugins.
