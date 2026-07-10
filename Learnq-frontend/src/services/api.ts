import axios from 'axios';

// Create an axios instance with default config
const api = axios.create({
    baseURL: 'http://127.0.0.1:8100', // FastAPI backend URL
    headers: {
        'Content-Type': 'application/json',
    },
});

// Request interceptor to add the auth token to requests
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Response interceptor to handle errors
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response && (error.response.status === 403 || error.response.status === 401)) {
            window.dispatchEvent(new Event('token-expired'));
        }
        return Promise.reject(error);
    }
);

export const authService = {
    login: async (credentials: any) => {
        const response = await api.post('/api/v1/users/login', credentials);
        // Robustly check for token in various common locations
        const token = response.data.access_token ||
            response.data.token ||
            response.data.data?.access_token ||
            response.data.data?.token;

        if (token) {
            localStorage.setItem('token', token);

            // Helper to parse JWT
            const parseJwt = (token: string) => {
                try {
                    const base64Url = token.split('.')[1];
                    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
                    const jsonPayload = decodeURIComponent(window.atob(base64).split('').map(function (c) {
                        return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
                    }).join(''));
                    return JSON.parse(jsonPayload);
                } catch (e) {
                    return {};
                }
            };

            // Try to get name from response first, then token
            let name = response.data.user?.name ||
                response.data.data?.user?.name ||
                response.data.name ||
                response.data.data?.name;

            // If not in response, check token
            if (!name) {
                const decoded = parseJwt(token);
                name = decoded.name || decoded.sub || decoded.username || 'User';
            }

            localStorage.setItem('userName', name);
            window.dispatchEvent(new Event('auth-change'));
        }
        return response.data;
    },
    signup: async (userData: any) => {
        const response = await api.post('/api/v1/users/signup', userData);
        return response.data;
    },
    logout: () => {
        localStorage.removeItem('token');
        window.dispatchEvent(new Event('auth-change'));
    }
};

export const fileService = {
    uploadMedia: async (file: File, onProgress: (progress: number) => void) => {
        const formData = new FormData();
        formData.append('video', file);

        const response = await api.post('/api/v1/upload', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
            onUploadProgress: (progressEvent) => {
                if (progressEvent.total) {
                    const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                    onProgress(percentCompleted);
                }
            },
        });
        return response.data;
    },
    transcribeYoutube: async (url: string) => {
        const response = await api.post('/api/v1/transcribe-youtube', { url });
        return response.data;
    },
    transcribeMedia: async (fileName: string) => {
        const response = await api.post('/api/v1/transcribe', { fileName });
        return response.data;
    },
    getHistory: async () => {
        const response = await api.get('/api/v1/me/history');
        return response.data;
    },
    getVideoStreamUrl: (filename: string) => {
        // Extract just the filename from a full path like ./uploads/uuid.mp4
        const cleanName = filename.replace(/^\.\/uploads\//, '');
        return `http://127.0.0.1:8100/api/v1/video/${cleanName}`;
    }
};

export default api;
