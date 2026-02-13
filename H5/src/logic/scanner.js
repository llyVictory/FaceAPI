import jsQR from 'jsqr';

export const scanQRCode = (canvasContext, width, height) => {
    if (!canvasContext || width === 0 || height === 0) return null;

    try {
        const imageData = canvasContext.getImageData(0, 0, width, height);
        const code = jsQR(imageData.data, imageData.width, imageData.height, {
            inversionAttempts: "dontInvert",
        });

        if (code) {
            return {
                data: code.data,
                location: code.location
            };
        }
    } catch (e) {
        console.error("QR Scan Error:", e);
    }
    return null;
};
