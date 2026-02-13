import { CONFIG } from '../config';

export const verifyIdentity = async (blob, address) => {
    const formData = new FormData();
    formData.append('file', blob, 'capture.jpg');
    formData.append('token', 'demo_token'); // Mock token
    formData.append('address', address);

    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}/api/face/verify`, {
            method: 'POST',
            body: formData,
            // mode: 'cors' // Vite proxy or Backend CORS handles this
        });

        if (!response.ok) {
            throw new Error(`Server Error: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error("API Verification Failed:", error);
        throw error;
    }
};
