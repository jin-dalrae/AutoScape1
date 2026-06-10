/**
 * API Configuration
 * 
 * Centralized configuration for backend API endpoints.
 * Uses environment variables for production deployment.
 */

// RAG Enhancement API - Python backend for plant catalog and budget calculation
// Uses localhost in dev, Cloud Run in production
export const RAG_API_BASE = import.meta.env.VITE_RAG_API_URL ||
    (import.meta.env.DEV ? 'http://localhost:8002' : 'https://rag-api-tejipfhw2q-uc.a.run.app');

// Firebase Cloud Functions - Video generation
export const CLOUD_FUNCTIONS_BASE = import.meta.env.VITE_CLOUD_FUNCTIONS_URL ||
    'https://us-central1-autoscape-dfc00.cloudfunctions.net';

// Stripe Checkout API Base URL
const STRIPE_API_BASE = import.meta.env.VITE_STRIPE_API_BASE ||
    'http://localhost:8003';

// Endpoints
export const API_ENDPOINTS = {
    // RAG Enhancement API
    enhanceWithRag: `${RAG_API_BASE}/api/enhance-with-rag`,
    generateVideoLocal: `${RAG_API_BASE}/api/generate-video`,
    generate3DLocal: `${RAG_API_BASE}/api/generate-3d`,
    get3DStatus: `${RAG_API_BASE}/api/3d-status`,
    freepikSearch: `${RAG_API_BASE}/api/freepik/search`,
    health: `${RAG_API_BASE}/health`,

    // Stripe Checkout API
    createCheckoutSession: `${STRIPE_API_BASE}/api/create-checkout-session`,
    createPortalSession: `${STRIPE_API_BASE}/api/create-portal-session`,
    stripeWebhook: `${STRIPE_API_BASE}/api/webhook`,

    // Cloud Functions (for production)
    generateVideoCloud: `${CLOUD_FUNCTIONS_BASE}/generate_video`,
    generate3DCloud: `${CLOUD_FUNCTIONS_BASE}/generate_3d`,
};

// Use Cloud Functions for video in production, local API for development
export const getVideoEndpoint = () => {
    // If we have a RAG API configured (local dev), use it
    // Otherwise use Cloud Functions (production)
    if (import.meta.env.DEV) {
        return API_ENDPOINTS.generateVideoLocal;
    }
    return API_ENDPOINTS.generateVideoCloud;
};

// Get 3D generation endpoint
export const get3DEndpoint = () => {
    if (import.meta.env.DEV) {
        return API_ENDPOINTS.generate3DLocal;
    }
    return API_ENDPOINTS.generate3DCloud;
};

// Get 3D status endpoint
export const get3DStatusEndpoint = (taskId: string) => {
    return `${RAG_API_BASE}/api/3d-status/${taskId}`;
};
