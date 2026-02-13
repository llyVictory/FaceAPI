import { reactive } from 'vue';

export const appState = reactive({
    currentStep: 0,

    // Selected User for 1:1 verification
    currentUser: null, // { id, name }
    targetFeature: null, // Float32Array (512,)

    // Verification Result
    verificationResult: {
        score: 0,
        isMatch: false,
        status: ''
    },

    reset() {
        this.currentStep = 0;
        this.verificationResult = { score: 0, isMatch: false, status: '' };
        // We might keep currentUser selected for convenience
    }
});
