import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { apiClient } from '@/api/client'

interface User {
  id: string
  username: string
  email?: string
  role: string
}

interface LoginData {
  username: string
  password: string
}

interface AuthToken {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('access_token'))
  const refreshToken = ref<string | null>(localStorage.getItem('refresh_token'))
  const user = ref<User | null>(null)

  const isAuthenticated = computed(() => !!token.value)

  async function login(loginData: LoginData) {
    try {
      const response = await apiClient.post<AuthToken>('/auth/login', loginData)

      token.value = response.access_token
      refreshToken.value = response.refresh_token

      localStorage.setItem('access_token', response.access_token)
      localStorage.setItem('refresh_token', response.refresh_token)

      const currentUser = await fetchUser()
      return !!currentUser
    } catch (error) {
      console.error('Login failed:', error)
      return false
    }
  }

  async function register(userData: { username: string; password: string }) {
    await apiClient.post('/auth/register', userData)
    return true
  }

  async function fetchUser() {
    try {
      user.value = await apiClient.get<User>('/auth/me')
      return user.value
    } catch (error) {
      console.error('Fetch current user failed:', error)
      logout()
      return null
    }
  }

  function logout() {
    token.value = null
    refreshToken.value = null
    user.value = null

    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  async function refreshAccessToken() {
    if (!refreshToken.value) {
      logout()
      return false
    }

    try {
      const response = await apiClient.post<AuthToken>('/auth/refresh', {
        refresh_token: refreshToken.value
      })

      token.value = response.access_token
      localStorage.setItem('access_token', response.access_token)

      return true
    } catch (error) {
      console.error('Refresh access token failed:', error)
      logout()
      return false
    }
  }

  return {
    token,
    user,
    isAuthenticated,
    login,
    register,
    logout,
    fetchUser,
    refreshAccessToken
  }
})
