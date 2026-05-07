const fs = require('fs');
const path = require('path');

function walk(dir) {
  let results = [];
  const list = fs.readdirSync(dir);
  list.forEach(file => {
    const filePath = path.join(dir, file);
    const stat = fs.statSync(filePath);
    if (stat && stat.isDirectory()) {
      results = results.concat(walk(filePath));
    } else if (filePath.endsWith('.jsx') || filePath.endsWith('.css')) {
      results.push(filePath);
    }
  });
  return results;
}

const files = walk('./src');
files.forEach(file => {
  let content = fs.readFileSync(file, 'utf8');
  let changed = false;
  
  if (content.includes('#0a0f1a')) { 
    content = content.replace(/#0a0f1a/g, 'var(--bg-surface)'); 
    changed = true; 
  }
  if (content.includes('#0d1520')) { 
    content = content.replace(/#0d1520/g, 'var(--bg-panel)'); 
    changed = true; 
  }
  if (content.includes('#ff6b00')) { 
    content = content.replace(/#ff6b00/g, 'var(--high-sev)'); 
    changed = true; 
  }
  if (content.includes('#020409')) { 
    content = content.replace(/#020409/g, 'var(--bg-primary)'); 
    changed = true; 
  }
  
  if (changed) {
    fs.writeFileSync(file, content);
    console.log('Updated ' + file);
  }
});
