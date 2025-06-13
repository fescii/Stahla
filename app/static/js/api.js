export default class APIManager {
  constructor(baseURL = '', defaultTimeout = 9500, cacheVersion = 'v1') {
    this.baseURL = baseURL;
    this.defaultTimeout = defaultTimeout;
    this.pendingRequests = new Map();
    this.cacheName = `api-cache-${cacheVersion}`;

    this.contentTypes = {
      json: 'application/json',
      text: 'text/plain',
      html: 'text/html',
      xml: 'application/xml',
      form: 'application/x-www-form-urlencoded',
      multipart: 'multipart/form-data',
      binary: 'application/octet-stream',
    };

    // Initialize cache
    this.initCache();
  } async initCache() {
    if ('caches' in window) {
      // Clear all caches first in production to fix mixed content issues
      if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
        await this.clearAllCaches();
      }

      // Open or create the cache
      await caches.open(this.cacheName);

      // Clear any cached HTTP requests if we're on HTTPS
      if (window.location.protocol === 'https:') {
        await this.clearHttpCaches();
      }
    } else {
      console.warn('Cache Storage API is not available in this browser');
    }
  }

  async clearHttpCaches() {
    try {
      const cache = await caches.open(this.cacheName);
      const requests = await cache.keys();

      for (const request of requests) {
        if (request.url.startsWith('http://')) {
          console.log('Clearing HTTP cache for:', request.url);
          await cache.delete(request);
          // Also clear localStorage metadata
          const key = `${this.cacheName}-metadata-${request.url}-${request.method}`;
          localStorage.removeItem(key);
        }
      }
    } catch (error) {
      console.warn('Failed to clear HTTP caches:', error);
    }
  }

  #processHeaders(options = {}) {
    const contentType = options?.content;
    const headers = new Headers();

    if (contentType) {
      headers.set('Content-Type', this.contentTypes[contentType]);
    }

    // If options.headers is an object, iterate over it and set each header
    if (options.headers && typeof options.headers === 'object') {
      Object.entries(options.headers).forEach(([key, value]) => {
        headers.set(key, value);
      });
    }

    return headers;
  }

  #generateCacheKey(url, options = {}) {
    console.log('Generating cache key for URL:', url);
    const normalizedOptions = { ...options };
    delete normalizedOptions.signal;
    const request = new Request(url, {
      ...normalizedOptions,
      method: options.method || 'GET',
    });
    console.log('Generated Request object URL:', request.url);
    return request;
  }

  async #storeCacheMetadata(request, data, cacheOptions) {
    const metadata = {
      data,
      createdAt: new Date().toISOString(),
      expiryDate: new Date(Date.now() + (cacheOptions.duration || 300000)).toISOString(),
    };

    // Store metadata in localStorage for quick access
    localStorage.setItem(
      `${this.cacheName}-metadata-${request.url}-${request.method}`,
      JSON.stringify(metadata)
    );

    return metadata;
  }

  async #getCacheMetadata(request) {
    const key = `${this.cacheName}-metadata-${request.url}-${request.method}`;
    const metadata = localStorage.getItem(key);
    return metadata ? JSON.parse(metadata) : null;
  }

  async #removeCacheMetadata(request) {
    const key = `${this.cacheName}-metadata-${request.url}-${request.method}`;
    localStorage.removeItem(key);
  }

  async #handleCache(request, cacheOptions) {
    if (!cacheOptions?.allow || !('caches' in window)) return null;

    const cache = await caches.open(this.cacheName);
    const cachedResponse = await cache.match(request);

    if (cachedResponse) {
      const metadata = await this.#getCacheMetadata(request);
      if (metadata) {
        const now = new Date();
        const expiryDate = new Date(metadata.expiryDate);

        if (now < expiryDate) {
          return metadata.data;
        }
        // Cache expired, remove it
        await this.#removeFromCache(request);
      }
    }
    return null;
  }

  async #setCacheData(request, data, cacheOptions) {
    if (!cacheOptions?.allow || !('caches' in window)) return;

    const cache = await caches.open(this.cacheName);

    // Store the response in the cache
    const response = new Response(JSON.stringify(data), {
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': `max-age=${Math.floor((cacheOptions.duration || 300000) / 1000)}`,
      },
    });

    await cache.put(request, response);
    await this.#storeCacheMetadata(request, data, cacheOptions);
  }

  async #removeFromCache(request) {
    if ('caches' in window) {
      const cache = await caches.open(this.cacheName);
      await cache.delete(request);
      await this.#removeCacheMetadata(request);
    }
  }

  async #processResponse(response) {
    const contentType = response.headers.get('Content-Type');

    if (contentType?.includes('application/json')) {
      return response.json();
    } else if (contentType?.includes('text/')) {
      return response.text();
    } else if (contentType?.includes('application/octet-stream')) {
      return response.blob();
    }

    try {
      return await response.json();
    } catch {
      return response.text();
    }
  }

  async #request(url, options = {}, cacheOptions = {}) {
    // Construct the full URL
    let fullURL;
    if (url.startsWith('http://') || url.startsWith('https://')) {
      fullURL = url;
    } else if (url.startsWith('//')) {
      fullURL = window.location.protocol + url;
    } else {
      fullURL = this.baseURL + url;
    }

    // Force HTTPS in production (bulletproof approach)
    if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
      if (fullURL.startsWith('http://')) {
        console.warn('Converting HTTP to HTTPS:', fullURL);
        fullURL = fullURL.replace(/^http:\/\//, 'https://');
      }
    }

    // Add cache-busting parameter in production to avoid cached HTTP requests
    if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
      const separator = fullURL.includes('?') ? '&' : '?';
      fullURL += `${separator}_cb=${Date.now()}`;
    }

    console.log('API Request - Base URL:', this.baseURL, 'Relative URL:', url, 'Final URL:', fullURL);
    const request = this.#generateCacheKey(fullURL, options);

    // Check cache first - will automatically handle expiry
    const cachedData = await this.#handleCache(request, cacheOptions);
    if (cachedData) return cachedData;

    // Handle concurrent requests
    const pendingKey = `${request.url}-${request.method}`;
    const pendingRequest = this.pendingRequests.get(pendingKey);
    if (pendingRequest) return pendingRequest;

    const controller = new AbortController();
    const timeoutId = setTimeout(
      () => controller.abort(),
      options.timeout || this.defaultTimeout
    );

    const processedHeaders = this.#processHeaders(options);

    // Handle FormData (for file uploads)
    let body = options.body;
    if (body instanceof FormData) {
      // Do not set Content-Type header for FormData; the browser will handle it
      processedHeaders.delete('Content-Type');
    } else if (body && typeof body === 'object') {
      if (processedHeaders.get('Content-Type') === this.contentTypes.json) {
        body = JSON.stringify(body);
      } else if (processedHeaders.get('Content-Type') === this.contentTypes.form) {
        const formData = new URLSearchParams();
        Object.entries(body).forEach(([key, value]) => {
          formData.append(key, value);
        });
        body = formData;
      }
    }

    const fetchPromise = (async () => {
      try {
        console.log('About to fetch - Using URL directly:', fullURL);
        console.log('About to fetch - Method:', options.method);
        console.log('About to fetch - Headers:', [...processedHeaders.entries()]);

        const response = await fetch(fullURL, {
          method: options.method,
          body,
          headers: processedHeaders,
          signal: controller.signal,
          credentials: 'include',
        });

        console.log('Fetch completed - Response URL:', response.url);
        console.log('Fetch completed - Response Status:', response.status);

        const data = await this.#processResponse(response);
        await this.#setCacheData(request, data, cacheOptions);
        return data;
      } catch (error) {
        if (error.name === 'AbortError') {
          throw new Error('Request timed out');
        }
        throw error;
      } finally {
        clearTimeout(timeoutId);
        this.pendingRequests.delete(pendingKey);
      }
    })();

    this.pendingRequests.set(pendingKey, fetchPromise);
    return fetchPromise;
  }

  // HTTP method implementations
  async get(url, options = {}, cacheOptions = {}) {
    return this.#request(url, { ...options, method: 'GET' }, cacheOptions);
  }

  async post(url, options = {}, cacheOptions = {}) {
    return this.#request(url, { ...options, method: 'POST' }, cacheOptions);
  }

  async put(url, options = {}, cacheOptions = {}) {
    return this.#request(url, { ...options, method: 'PUT' }, cacheOptions);
  }

  async patch(url, options = {}, cacheOptions = {}) {
    return this.#request(url, { ...options, method: 'PATCH' }, cacheOptions);
  }

  async delete(url, options = {}, cacheOptions = {}) {
    return this.#request(url, { ...options, method: 'DELETE' }, cacheOptions);
  }

  // File upload method
  async uploadFile(url, file, options = {}) {
    if (!file || !(file instanceof File)) {
      throw new Error('Invalid file provided');
    }

    const formData = new FormData();
    formData.append('file', file);

    return this.post(url, { ...options, body: formData });
  }

  // Cache management methods
  async clearCache(url = null, options = {}) {
    if ('caches' in window) {
      if (url) {
        const request = this.#generateCacheKey(this.baseURL + url, options);
        await this.#removeFromCache(request);
      } else {
        await caches.delete(this.cacheName);
        await this.initCache();
        // Clear all metadata
        const keys = Object.keys(localStorage);
        keys.forEach((key) => {
          if (key.startsWith(`${this.cacheName}-metadata-`)) {
            localStorage.removeItem(key);
          }
        });
      }
    }
  }

  async clearAllCaches() {
    try {
      // Clear all Cache Storage
      if ('caches' in window) {
        const cacheNames = await caches.keys();
        for (const cacheName of cacheNames) {
          console.log('Deleting cache:', cacheName);
          await caches.delete(cacheName);
        }
      }

      // Clear all localStorage items related to API cache
      const keysToRemove = [];
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.includes('api-cache')) {
          keysToRemove.push(key);
        }
      }
      keysToRemove.forEach(key => {
        console.log('Clearing localStorage cache:', key);
        localStorage.removeItem(key);
      });

      console.log('All caches cleared successfully');
    } catch (error) {
      console.warn('Failed to clear all caches:', error);
    }
  }

  async getCacheSize() {
    if ('caches' in window) {
      const cache = await caches.open(this.cacheName);
      const keys = await cache.keys();
      return keys.length;
    }
    return 0;
  }

  async getCacheStatus(url, options = {}) {
    if (!('caches' in window)) return null;

    const request = this.#generateCacheKey(this.baseURL + url, options);
    const metadata = await this.#getCacheMetadata(request);

    if (!metadata) return null;

    const now = new Date();
    const expiryDate = new Date(metadata.expiryDate);

    return {
      isValid: now < expiryDate,
      createdAt: new Date(metadata.createdAt),
      expiryDate: expiryDate,
      timeRemaining: expiryDate.getTime() - now.getTime(),
    };
  }

  getContentTypes() {
    return { ...this.contentTypes };
  }
}