import fs from 'fs';
import https from 'https';
import path from 'path';

const url = 'https://raw.githubusercontent.com/justadudewhohacks/face-api.js/master/dist/face-api.min.js';
const outputDir = path.join(process.cwd(), 'public', 'js');
const filePath = path.join(outputDir, 'face-api.min.js');

if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
}

const fileStream = fs.createWriteStream(filePath);

console.log(`Downloading face-api.min.js...`);

https.get(url, (response) => {
    if (response.statusCode === 200) {
        response.pipe(fileStream);
        fileStream.on('finish', () => {
            fileStream.close();
            console.log(`Finished downloading face-api.min.js`);
        });
    } else {
        console.error(`Failed to download: Status ${response.statusCode}`);
        fileStream.close();
        fs.unlinkSync(filePath);
    }
}).on('error', (err) => {
    fs.unlinkSync(filePath);
    console.error(`Error downloading: ${err.message}`);
});
