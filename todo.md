https://www.redblobgames.com/grids/hexagons/#distances

https://kirankoduru.github.io/python/sublime-text-ninja.html


- add homing projectiles (poppy)
- look into why projectiles sometimes are stuck on bottom left corner (prob b/c owner or target died?)


- TODO: make other star gaurdians
  - zoe
    - cc



- show dmg numbers
  - maybe also source?


vvv make this so logging & printing looks nice
- global timestamp from board rather than each champion?


propegate errors from async tasks somehow

- try out: what happens when a champion gets full mana while not attacking? is it queued properly?
  - what happens when champion dies mid action?




champions general
- traits
- damage logic
  - dmg need to be responded to (eg thronmail)
  - this response needs a callback to process too
  - on-hit modifiers?

- make nonexistent unit removal not throw err but return True/False


Code
- enums
- logs