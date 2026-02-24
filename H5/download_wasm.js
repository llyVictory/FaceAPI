import fs from 'fs';
import https from 'https';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const version = '1.17.1';
const baseUrl = `https://cdn.jsdelivr.net/npm/onnxruntime-web@${version}/dist/`;
const wasmFiles = [
    'ort-wasm.wasm',
    'ort-wasm-simd.wasm',
    'ort-wasm-threaded.wasm',
    'ort-wasm-simd-threaded.wasm'
];
const jsFiles = [
    'ort.min.js'
];

const publicDir = path.join(__dirname, 'public');
const jsOutputDir = path.join(publicDir, 'js');

if (!fs.existsSync(jsOutputDir)) {
    fs.mkdirSync(jsOutputDir, { recursive: true });
}

async function downloadFile(fileName, outDir) {
    const url = baseUrl + fileName;
    const filePath = path.join(outDir, fileName);
    const fileStream = fs.createWriteStream(filePath);

    return new Promise((resolve, reject) => {
        console.log(`Downloading ${fileName}...`);
        https.get(url, (response) => {
            if (response.statusCode === 200) {
                response.pipe(fileStream);
                fileStream.on('finish', () => {
                    fileStream.close();
                    console.log(`✅ Finished: ${fileName}`);
                    resolve();
                });
            } else {
                console.error(`❌ Failed: ${fileName} (Status ${response.statusCode})`);
                fileStream.close();
                if (fs.existsSync(filePath)) fs.unlinkSync(filePath);
                reject(new Error(`Status ${response.statusCode}`));
            }
        }).on('error', (err) => {
            if (fs.existsSync(filePath)) fs.unlinkSync(filePath);
            console.error(`❌ Error: ${fileName} (${err.message})`);
            reject(err);
        });
    });
}

async function main() {
    for (const file of wasmFiles) {
        try {
            await downloadFile(file, publicDir);
        } catch (e) {
            console.warn(`跳过失败的文件: ${file}`);
        }
    }
    for (const file of jsFiles) {
        try {
            await downloadFile(file, jsOutputDir);
        } catch (e) {
            console.warn(`跳过失败的文件: ${file}`);
        }
    }
    console.log('所有资源处理完成');
}

main();
