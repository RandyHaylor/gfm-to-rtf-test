const htmlToRtf = require('html-to-rtf');
const fs = require('fs');
const path = require('path');
const sharp = require('sharp');

const inputHtmlPath = process.argv[2] || 'README-github.html';
const outputRtfPath = process.argv[3] || 'README.rtf';
const baseDirForImages = process.argv[4] || path.dirname(path.resolve(inputHtmlPath));

// Max page dimensions in pixels (letter page 8.5x11 minus 1" margins each side)
const MAX_WIDTH_PX = 468;
const MAX_HEIGHT_PX = 648;

async function main() {
    let html = fs.readFileSync(inputHtmlPath, 'utf8');

    // Phase 1: Extract local images, replace with text markers, store data
    const imageMap = {};
    let imgIdx = 0;
    html = html.replace(/<img\s+[^>]*?>/gi, (tag) => {
        const srcMatch = tag.match(/src="([^"]+)"/);
        if (!srcMatch) return '';
        const src = srcMatch[1];
        if (src.startsWith('data:') || src.startsWith('http://') || src.startsWith('https://')) return tag;
        const widthMatch = tag.match(/width="(\d+)"/);
        const heightMatch = tag.match(/height="(\d+)"/);
        const key = `IMGEMBED${imgIdx}END`;
        imageMap[key] = { src, width: widthMatch ? parseInt(widthMatch[1]) : 0, height: heightMatch ? parseInt(heightMatch[1]) : 0 };
        imgIdx++;
        return `<p>${key}</p>`;
    });

    // Phase 2: Convert HTML to RTF
    let rtf = htmlToRtf.convertHtmlToRtf(html);

    // Phase 3: Find IMGEMBED markers in RTF, replace with \pict blocks
    for (const [key, info] of Object.entries(imageMap)) {
        const imagePath = path.resolve(baseDirForImages, info.src);
        if (!fs.existsSync(imagePath)) {
            rtf = rtf.replace(key, `[Image not found: ${info.src}]`);
            continue;
        }
        const buffer = fs.readFileSync(imagePath);
        const ext = path.extname(info.src).toLowerCase();
        const picType = (ext === '.jpg' || ext === '.jpeg') ? 'jpegblip' : 'pngblip';

        // Read native size
        const metadata = await sharp(buffer).metadata();
        const nativeW = metadata.width || 0;
        const nativeH = metadata.height || 0;

        // Calculate display dimensions
        let w = info.width || nativeW;
        let h = info.height;
        if (w && !h && nativeW && nativeH) {
            h = Math.round(w * nativeH / nativeW);
        } else if (h && !w && nativeW && nativeH) {
            w = Math.round(h * nativeW / nativeH);
        } else if (!h) {
            h = nativeH;
        }

        // Clamp to page dimensions
        if (w > MAX_WIDTH_PX) {
            const scale = MAX_WIDTH_PX / w;
            w = MAX_WIDTH_PX;
            h = Math.round(h * scale);
        }
        if (h > MAX_HEIGHT_PX) {
            const scale = MAX_HEIGHT_PX / h;
            h = MAX_HEIGHT_PX;
            w = Math.round(w * scale);
        }

        // Downscale image data if larger than display size
        let outputBuffer = buffer;
        if (nativeW > w || nativeH > h) {
            outputBuffer = await sharp(buffer).resize(w, h, { fit: 'inside' }).png().toBuffer();
        }

        const hex = outputBuffer.toString('hex');
        let sizeParams = '';
        if (w) sizeParams += `\\picwgoal${w * 15}`;
        if (h) sizeParams += `\\pichgoal${h * 15}`;

        rtf = rtf.replace(key, `{\\pict\\${picType}${sizeParams} ${hex}}`);
    }

    fs.writeFileSync(outputRtfPath, rtf);
    console.log(`Converted: ${inputHtmlPath} -> ${outputRtfPath}`);
}

main();
