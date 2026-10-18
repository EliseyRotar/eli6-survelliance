const imgs = Array.from(document.querySelectorAll('img')).map(i => i.src).filter(s => s && !s.includes('/RRSS/'));
const ifr = Array.from(document.querySelectorAll('iframe')).map(f => f.src);
const vids = Array.from(document.querySelectorAll('video, source')).map(v => v.src || v.currentSrc || '');
const links = Array.from(document.querySelectorAll('a')).map(a => a.href).filter(h => h && /cam/i.test(h));
JSON.stringify({imgs, ifr, vids, links}, null, 1).slice(0, 5000);
