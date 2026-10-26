from pathlib import Path
assert env.cr.dbname == 'LIVE_3_AGUST_2026-1147AM', env.cr.dbname
exec(Path('/mnt/custom-addons/docs/payment_tax/configure.py').read_text())
env.cr.commit()
print('COMMITTED payment tax configuration to', env.cr.dbname)
