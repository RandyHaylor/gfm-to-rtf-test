const htmlToRtf = require('html-to-rtf');
const fs = require('fs');
const path = require('path');

const inputHtmlPath = process.argv[2] || 'README-github.html';
const outputRtfPath = process.argv[3] || 'README.rtf';
const baseDirForImages = process.argv[4] || path.dirname(inputHtmlPath);

let html = fs.readFileSync(inputHtmlPath, 'utf8');

// Collect local images and their hex-encoded data for RTF embedding
const imageEmbeds = {};
html.replace(/<img\s+[^>]*?src="([^"]+)"[^>]*?>/g, (fullMatch, src) => {
    if (src.startsWith('data:') || src.startsWith('http://') || src.startsWith('https://')) return;
    const imagePath = path.resolve(baseDirForImages, src);
    if (fs.existsSync(imagePath)) {
        const imageBuffer = fs.readFileSync(imagePath);
        imageEmbeds[src] = imageBuffer.toString('hex');
    }
});

// Convert HTML to RTF
let rtf = htmlToRtf.convertHtmlToRtf(html);

// Post-process: find image placeholders or insert embedded images
// The html-to-rtf package likely strips <img> tags, so we inject after conversion
// by looking for a safe insertion point (before the closing })
for (const [src, hexData] of Object.entries(imageEmbeds)) {
    const pictBlock = `{\\pard\\sb120\\sa120\\qc{\\pict\\pngblip\\picw0\\pich0\\picwgoal5000\\pichgoal3000 ${hexData}}\\par}`;
    // Insert before the final closing brace
    const lastBrace = rtf.lastIndexOf('}');
    rtf = rtf.slice(0, lastBrace) + '\n' + pictBlock + '\n' + rtf.slice(lastBrace);
}

fs.writeFileSync(outputRtfPath, rtf);
console.log(`Converted: ${inputHtmlPath} -> ${outputRtfPath}`);
console.log(`Embedded ${Object.keys(imageEmbeds).length} image(s)`);
