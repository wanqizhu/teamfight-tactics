https://www.redblobgames.com/grids/hexagons/#distances

https://kirankoduru.github.io/python/sublime-text-ninja.html


vvv make this so logging & printing looks nice
- global timestamp from board rather than each champion?


- read in SPELL_DAMAGE from .json

propegate errors from async tasks somehow

- try out: what happens when a champion gets full mana while not attacking? is it queued properly?
  - what happens when champion dies mid action?




champions general
- traits
- death
  - remove from board
  - reset targeting
- damage logic
  - dmg need to be responded to (eg thronmail)
  - this response needs a callback to process too
  - on-hit modifiers?

- make nonexistent unit removal not throw err but return True/False


Code
- property setters
- enums
- logs


The correct way to line target is to have a projectile class w/ predefined trajectory --> enables Braum