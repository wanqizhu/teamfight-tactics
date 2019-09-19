- targeting
  - check untargetability instead of `self.target is None`

vvv make this so logging & printing looks nice
- global timestamp from board rather than each champion?


- should spells cast even while waiting for an autoattack?


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