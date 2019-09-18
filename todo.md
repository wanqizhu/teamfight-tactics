- targeting
  - check untargetability instead of `self.target is None`

- global timestamp from board rather than each champion?


ahri
- line targetting


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