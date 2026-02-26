/**
 * 3. API CONFIGURATION (NO LOCALHOST IN PROD)
 * Environment-based configuration with fail-loud behavior.
 */
const API_URL = import.meta.env.VITE_API_URL || "/api";

export const getApiUrl = () => {
    return API_URL;
};

export const getApiKey = () => {
    return import.meta.env.VITE_API_KEY || "";
};

export default getApiUrl;
