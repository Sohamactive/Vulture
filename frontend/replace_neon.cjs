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
  
  if (content.includes('#00f5ff')) { 
    content = content.replace(/#00f5ff/gi, '#ffffff'); 
    changed = true; 
  }
  if (content.includes('rgba(0,245,255,')) {
    content = content.replace(/rgba\(0,245,255,/g, 'rgba(255,255,255,');
    changed = true;
  }
  if (content.includes('--cyan-dim:      #00a8b5')) {
    content = content.replace(/--cyan-dim:      #00a8b5/g, '--cyan-dim:      #94a3b8');
    changed = true;
  }
  
  if (changed) {
    fs.writeFileSync(file, content);
    console.log('Updated ' + file);
  }
});
