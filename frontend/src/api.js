const API_PREFIX = '/api'

async function request(path, options = {}) {
  const response = await fetch(`${API_PREFIX}${path}`, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {})
    },
    ...options
  })
  const payload = await response.json().catch(() => ({}))
  if (!response.ok || payload.ok === false) {
    throw new Error(payload.message || `请求失败：${response.status}`)
  }
  return payload.data
}

export const api = {
  site: () => request('/site'),
  me: () => request('/auth/me'),
  login: (data) => request('/auth/login', { method: 'POST', body: JSON.stringify(data) }),
  register: (data) => request('/auth/register', { method: 'POST', body: JSON.stringify(data) }),
  logout: () => request('/auth/logout', { method: 'POST' }),
  categories: () => request('/categories'),
  blogs: (params = {}) => {
    const query = new URLSearchParams(params)
    return request(`/blogs?${query.toString()}`)
  },
  blog: (id) => request(`/blogs/${id}`),
  comments: (id) => request(`/blogs/${id}/comments`),
  comment: (id, body) => request(`/blogs/${id}/comments`, {
    method: 'POST',
    body: JSON.stringify({ body })
  }),
  stats: () => request('/admin/stats'),
  createBlog: (data) => request('/admin/blogs', { method: 'POST', body: JSON.stringify(data) }),
  updateBlog: (id, data) => request(`/admin/blogs/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteBlog: (id) => request(`/admin/blogs/${id}`, { method: 'DELETE' }),
  createCategory: (data) => request('/admin/categories', { method: 'POST', body: JSON.stringify(data) })
}
