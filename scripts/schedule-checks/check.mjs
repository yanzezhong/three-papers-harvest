import { execFileSync } from 'node:child_process';
const py = [
  "import sqlite3",
  "try:",
  "    db = sqlite3.connect('D:/three-papers-harvest/harvest.db', timeout=5)",
  "    pend = db.execute(\"SELECT COUNT(*) FROM articles2026 WHERE ph_hit=1 AND md_path IS NULL\").fetchone()[0]",
  "    imgfill = db.execute(\"SELECT COUNT(*) FROM articles2026 a WHERE a.md_path IS NOT NULL AND NOT EXISTS(SELECT 1 FROM images i WHERE i.article_url=a.url)\").fetchone()[0]",
  "    nls = db.execute(\"SELECT COUNT(*) FROM listings_scanned\").fetchone()[0]",
  "    print(pend, imgfill, nls)",
  "except Exception as e:",
  "    print('ERR', e)"
].join('\n');
let out;
try {
  out = execFileSync('python', ['-X', 'utf8', '-c', py], { encoding: 'utf8', timeout: 30000 });
} catch (e) {
  console.error('precheck: db query failed:', String(e).slice(0, 200));
  process.exit(1);
}
const parts = out.trim().split(/\s+/);
if (parts[0] === 'ERR') { console.error('precheck ERR:', out); process.exit(1); }
const pend = Number(parts[0]), imgfill = Number(parts[1]), nls = Number(parts[2]);
console.error(`precheck: pend=${pend} imgfill=${imgfill} nls=${nls}`);
if (Number.isNaN(pend) || Number.isNaN(nls)) { console.error('precheck: parse fail'); process.exit(1); }
if (pend > 0 || imgfill > 0 || nls < 100) {
  console.log('CINDY_PRECHECK_OK');
  process.exit(0);
}
console.error('precheck: nothing to do, skip this run');
console.log('CINDY_PRECHECK_OK');
process.exit(2);
