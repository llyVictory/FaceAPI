// Helper to wait for the global script to load
const waitForGlobalApi = () => {
    return new Promise((resolve, reject) => {
        if (window.faceapi) {
            console.log("face-api.js 已加载");
            return resolve(window.faceapi);
        }

        console.log("等待 face-api.js 加载...");
        let attempts = 0;
        const interval = setInterval(() => {
            attempts++;
            if (window.faceapi) {
                clearInterval(interval);
                console.log("face-api.js 加载成功！");
                resolve(window.faceapi);
            } else if (attempts > 50) { // Wait 5 seconds max
                clearInterval(interval);
                console.error("face-api.js 加载超时");
                reject(new Error("Timeout waiting for face-api.js"));
            }
        }, 100);
    });
};

// Proxied export for direct usage (e.g. in Step2)
// This allows other files to import 'api' and use it, 
// ensuring they get the global object when they actually access properties.
export const api = new Proxy({}, {
    get: function (target, prop, receiver) {
        if (!window.faceapi) {
            console.warn(`Accessing faceapi.${String(prop)} before load!`);
            return undefined;
        }
        return Reflect.get(window.faceapi, prop, receiver);
    }
});

export class FaceEngine {
    constructor() {
        this.modelsLoaded = false;
        this.detectorOptions = null; // Initialize later
    }

    async loadModels() {
        if (this.modelsLoaded) return;

        try {
            // WAIT for the global object
            const faceapi = await waitForGlobalApi();

            // DEBUG: Print all keys to understand what's available
            console.log("FaceAPI Object Keys:", Object.keys(faceapi));
            console.log("FaceAPI.nets:", faceapi.nets);
            if (faceapi.nets) {
                console.log("FaceAPI.nets Keys:", Object.keys(faceapi.nets));
            }

            // Now safe to init options
            if (!this.detectorOptions) {
                this.detectorOptions = new faceapi.TinyFaceDetectorOptions({ inputSize: 224, scoreThreshold: 0.5 });
            }

            const MODEL_URL = '/models';
            console.log('Loading models from:', MODEL_URL);

            await Promise.all([
                faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL),
                faceapi.nets.faceLandmark68Net.loadFromUri(MODEL_URL),
                faceapi.nets.faceRecognitionNet.loadFromUri(MODEL_URL)
            ]);
            this.modelsLoaded = true;
            console.log('Face models loaded');
        } catch (error) {
            console.error('Failed to load face models:', error);
            throw error;
        }
    }

    async detectSingleFace(videoEl) {
        if (!this.modelsLoaded || !window.faceapi) return null;

        // Use TinyFaceDetector for performance
        const detection = await window.faceapi.detectSingleFace(videoEl, this.detectorOptions)
            .withFaceLandmarks()
            .withFaceDescriptor();

        return detection;
    }

    // Calculate Eye Aspect Ratio (EAR) for blink detection
    calculateEAR(eye) {
        const p1 = eye[0];
        const p2 = eye[1];
        const p3 = eye[2];
        const p4 = eye[3];
        const p5 = eye[4];
        const p6 = eye[5];

        // Euclidean distance
        const dist = (p, q) => Math.hypot(p.x - q.x, p.y - q.y);

        const vertical1 = dist(p2, p6);
        const vertical2 = dist(p3, p5);
        const horizontal = dist(p1, p4);

        return (vertical1 + vertical2) / (2.0 * horizontal);
    }

    // Calculate Mouth Aspect Ratio (MAR)
    calculateMAR(mouth) {
        // Points for Inner Lip: Left(12), Top(14), Right(16), Bottom(18)
        // corresponding to 60, 62, 64, 66 in 68-point model

        if (!mouth || mouth.length < 19) return 0;

        const pLeft = mouth[12];
        const pRight = mouth[16];
        const pTop = mouth[14];
        const pBottom = mouth[18];

        const dist = (p, q) => Math.hypot(p.x - q.x, p.y - q.y);

        const horizontal = dist(pLeft, pRight);
        const vertical = dist(pTop, pBottom);

        if (horizontal === 0) return 0;
        return vertical / horizontal;
    }
}

export const faceEngine = new FaceEngine();
