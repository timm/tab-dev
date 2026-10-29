# tab-dev

Experiments on [tab](https://github.com/timm/tab). The library ships
clean; the rigs, the scores and the argument live here.

    ,/sh            work shell: sets TAB to ../tab, puts it on LUA_PATH
    ,/run nb        rerun an arm over moot, into cache/
    ,/again         fast edit -> figure loop
    etc/hpo.lua     sweep one knob against the label budget
    etc/charts.py   draw docs/*.png from cache/
    docs/rq.md      the research record: three questions, every table
    cache/          1,034 score csvs, one per dataset per arm
    attic/          dead code, kept as provenance

## Setup

Clone beside tab, so `../tab` resolves:

    cd ~/gh
    git clone https://github.com/timm/tab
    git clone https://github.com/timm/tab-dev
    cd tab-dev && ,/sh

`,/sh` exports `TAB`, `MOOT`, `CACHE` and `LUA_PATH`. An edit in
`../tab/tab.lua` takes effect here immediately -- tab is **not**
installed as a rock, deliberately. Override the location with
`TAB=/path/to/tab ,/sh`.

`,/run`, `,/again` and `etc/hpo.lua` all call **luajit** by name. tab
itself runs on any Lua 5.1-5.5 and its shebangs say `lua`; the speed
only matters here, where a sweep is thousands of fits. Results are
byte-identical either way -- the interpreter buys time, not numbers.

Data is [moot](https://github.com/timm/moot), expected at `~/gits/moot`.

## Results

See [docs/rq.md](docs/rq.md). Headline: range means over a few dozen
labels land within a few points of a gradient booster, at a fraction of
the cost, and the knobs are smaller than the noise.

(c) 2026 Tim Menzies, MIT license.
