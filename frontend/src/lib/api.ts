import axios, { AxiosInstance, AxiosRequestConfig } from "axios";

class ApiClient {
  private client: AxiosInstance;
  private tokenGetter: (() => Promise<string | null>) | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
      timeout: 60000,
    });

    // Inject Clerk auth token on every request
    this.client.interceptors.request.use(async (config) => {
      if (this.tokenGetter) {
        const token = await this.tokenGetter();
        if (token) {
          config.headers["Authorization"] = `Bearer ${token}`;
        }
      }
      return config;
    });

    this.client.interceptors.response.use(
      (r) => r,
      (error) => {
        const message =
          error.response?.data?.detail ??
          error.response?.data?.message ??
          error.message ??
          "Request failed";
        return Promise.reject(new Error(String(message)));
      }
    );
  }

  /** Call this once at app level with Clerk's getToken function */
  setTokenGetter(getter: () => Promise<string | null>) {
    this.tokenGetter = getter;
  }

  async get<T>(url: string, params?: Record<string, unknown>): Promise<T> {
    const { data } = await this.client.get<T>(url, { params });
    return data;
  }

  async post<T>(url: string, body: unknown, config?: AxiosRequestConfig): Promise<T> {
    const { data } = await this.client.post<T>(url, body, config);
    return data;
  }

  async postForm<T>(url: string, formData: FormData): Promise<T> {
    const { data } = await this.client.post<T>(url, formData, {
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 120000,
    });
    return data;
  }

  async patch<T>(url: string, body: unknown): Promise<T> {
    const { data } = await this.client.patch<T>(url, body);
    return data;
  }

  async delete(url: string): Promise<void> {
    await this.client.delete(url);
  }
}

export const apiClient = new ApiClient();
