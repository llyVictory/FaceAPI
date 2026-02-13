import fs from 'fs';
import https from 'https';
import path from 'path';

const models = [
  'tiny_face_detector_model-weights_manifest.json',
  'tiny_face_detector_model-shard1',
  'face_landmark_68_model-weights_manifest.json',
  'face_landmark_68_model-shard1',
  'face_recognition_model-weights_manifest.json',
  'face_recognition_model-shard1',
  'face_recognition_model-shard2'
];

const baseUrl = 'https://raw.githubusercontent.com/justadudewhohacks/face-api.js/master/weights/';
const outputDir = path.join(process.cwd(), 'public', 'models');

if (!fs.existsSync(outputDir)){
    fs.mkdirSync(outputDir, { recursive: true });
}

const downloadFile = (file) => {
  const url = baseUrl + file;
  const filePath = path.join(outputDir, file);
  
  if (fs.existsSync(filePath)) {
      console.log(`Skipping ${file} (already exists)`);
      return;
  }

  const fileStream = fs.createWriteStream(filePath);

  console.log(`Downloading ${file}...`);
  
  https.get(url, (response) => {
    if (response.statusCode === 200) {
        response.pipe(fileStream);
        fileStream.on('finish', () => {
            fileStream.close();
            console.log(`Finished ${file}`);
        });
    } else {
        console.error(`Failed to download ${file}: Status ${response.statusCode}`);
        fileStream.close();
        fs.unlinkSync(filePath); // Delete partial file
    }
  }).on('error', (err) => {
    fs.unlinkSync(filePath);
    console.error(`Error downloading ${file}: ${err.message}`);
  });
};

models.forEach(downloadFile);
