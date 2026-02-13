
// Wrapper for ONNX Runtime Web to run InsightFace model
// Needs 'ort' from global window object (via CDN)

export class InsightFaceEngine {
    constructor() {
        this.session = null;
        this.inputSize = [112, 112];

        // 尽早初始化全局配置
        if (window.ort) {
            window.ort.env.wasm.numThreads = 1;
            window.ort.env.wasm.proxy = false;
        }
    }

    async loadModel(modelUrl) {
        try {
            if (!window.ort) {
                throw new Error("onnxruntime-web not loaded");
            }

            const ort = window.ort;
            console.log("Using global ORT config:", ort.env.wasm);

            this.session = await ort.InferenceSession.create(modelUrl, {
                executionProviders: ['wasm'],
                graphOptimizationLevel: 'all'
            });

            console.log("✅ InsightFace 模型加载成功:", modelUrl);
        } catch (e) {
            console.error("❌ InsightFace 模型加载失败:", e);
            throw e;
        }
    }

    // 检测 WebAssembly SIMD 支持
    async detectSimdSupport() {
        try {
            // 检测方法 1：直接检测 WebAssembly.validate
            if (typeof WebAssembly !== 'undefined' && WebAssembly.validate) {
                // SIMD 测试字节码
                const simdTest = new Uint8Array([
                    0, 97, 115, 109, 1, 0, 0, 0, 1, 5, 1, 96, 0, 1, 123, 3,
                    2, 1, 0, 10, 10, 1, 8, 0, 65, 0, 253, 15, 253, 98, 11
                ]);
                return WebAssembly.validate(simdTest);
            }

            // 检测方法 2：User Agent 检测（iOS Safari）
            const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
            const isSafari = /Safari/.test(navigator.userAgent) && !/Chrome/.test(navigator.userAgent);

            if (isIOS && isSafari) {
                console.log('检测到 iOS Safari，禁用 SIMD');
                return false;
            }

            return true;
        } catch (e) {
            console.warn('SIMD 检测失败，默认禁用:', e);
            return false;
        }
    }

    // Preprocess image (Canvas/Image/Video -> Tensor)
    // We need to crop and resize the face to 112x112 first!
    // This helper assumes 'input' is already a 112x112 Canvas or ImageData
    async preprocess(input) {
        const width = this.inputSize[0];
        const height = this.inputSize[1];

        let ctx;
        if (input instanceof HTMLCanvasElement) {
            ctx = input.getContext('2d');
        } else {
            // Create temp canvas
            const canvas = document.createElement('canvas');
            canvas.width = width;
            canvas.height = height;
            ctx = canvas.getContext('2d');
            ctx.drawImage(input, 0, 0, width, height);
        }

        const imageData = ctx.getImageData(0, 0, width, height);
        const { data } = imageData; // RGBA

        // Transpose to (1, 3, 112, 112) and Normalize
        // InsightFace expects: (x - 127.5) / 128.0  OR  x / 255.0 depends on model.
        // Standard InsightFace w600k/mobilefacenet usually uses (x - 127.5) / 127.5

        const float32Data = new Float32Array(3 * width * height);

        for (let i = 0; i < width * height; i++) {
            const r = data[i * 4];
            const g = data[i * 4 + 1];
            const b = data[i * 4 + 2];

            // InsightFace ONNX (MobileFaceNet) usually expects RGB order
            // Normalization: (x - 127.5) / 127.5
            float32Data[i] = (r - 127.5) / 127.5;                   // R
            float32Data[i + width * height] = (g - 127.5) / 127.5;     // G
            float32Data[i + 2 * width * height] = (b - 127.5) / 127.5; // B
        }

        const tensor = new window.ort.Tensor('float32', float32Data, [1, 3, height, width]);
        return tensor;
    }

    async extractFeature(faceImageElement) {
        if (!this.session) throw new Error("Model not loaded");

        const inputTensor = await this.preprocess(faceImageElement);

        const feeds = {};
        feeds[this.session.inputNames[0]] = inputTensor;

        const results = await this.session.run(feeds);
        const output = results[this.session.outputNames[0]]; // usually "output" or "683"

        // Output is Float32Array (512,)
        return output.data;
    }

    cosineSimilarity(a, b) {
        if (a.length !== b.length) return 0;
        let dot = 0;
        let normA = 0;
        let normB = 0;
        for (let i = 0; i < a.length; i++) {
            dot += a[i] * b[i];
            normA += a[i] * a[i];
            normB += b[i] * b[i];
        }
        return dot / (Math.sqrt(normA) * Math.sqrt(normB));
    }
}

export const insightFace = new InsightFaceEngine();
