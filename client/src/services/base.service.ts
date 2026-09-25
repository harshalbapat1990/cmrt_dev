import http from '@/http';

export default class BaseService {
    endpoint: string;

    constructor(endpoint: string) {
        this.endpoint = endpoint;
    }

    async get(path = '') {
        try {
            const fullPath = path ? `${this.endpoint}${path}` : this.endpoint;
            const response = await http.get(fullPath);
            return response;
        } catch (error) {
            console.error(`BaseService.get() error:`, error);
            throw error;
        }
    }

    
async post(path = "", data = {}, config = {}) {
    try {
        const fullPath = path ? `${this.endpoint}${path}` : this.endpoint;

        const response = await http.post(fullPath, data, config);

        return response;
    } catch (error) {
        console.error(`BaseService.post() error:`, error);
        throw error;
    }
}


    async put(path = '', data = {}) {
        try {
            const fullPath = path ? `${this.endpoint}${path}` : this.endpoint;
            const response = await http.put(fullPath, data);
            return response;
        } catch (error) {
            console.error(`BaseService.put() error:`, error);
            throw error;
        }
    }

     async patch(path = '', data = {}) {
        try {
            const fullPath = path ? `${this.endpoint}${path}` : this.endpoint;
            const response = await http.patch(fullPath, data);
            return response;
        } catch (error) {
            console.error(`BaseService.patch() error:`, error);
            throw error;
        }
    }

    async delete(path = '') {
        try {
            const fullPath = path ? `${this.endpoint}${path}` : this.endpoint;
            const response = await http.delete(fullPath);
            return response;
        } catch (error) {
            console.error(`BaseService.delete() error:`, error);
            throw error;
        }
    }
}