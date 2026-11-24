// Fails if any source file renders raw HTML. React escapes everything it displays,
// except through dangerouslySetInnerHTML, so banning it keeps user content (event
// descriptions, names) from ever running as code (plan, Phase 3: XSS).
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

const banned = [/dangerouslySetInnerHTML/, /\.innerHTML\s*=/, /\beval\s*\(/, /new Function\s*\(/];
const problems = [];

function walk(dir) {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) walk(path);
    else if (/\.(jsx?|tsx?)$/.test(name)) {
      readFileSync(path, 'utf8').split('\n').forEach((line, i) => {
        if (banned.some((re) => re.test(line))) problems.push(`${path}:${i + 1}: ${line.trim()}`);
      });
    }
  }
}

walk('src');
if (problems.length) {
  console.error('Raw HTML / eval found:\n' + problems.join('\n'));
  process.exit(1);
}
console.log('OK: no raw HTML rendering or eval in src/');
