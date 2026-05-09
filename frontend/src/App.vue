<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import {
  ArrowLeft, BarChart3, Github, LogIn, LogOut, Mail, MessageCircle,
  PenLine, Plus, Search, Sparkles, UserRound
} from 'lucide-vue-next'
import { api } from './api'

const site = ref({})
const user = ref(null)
const blogs = ref([])
const categories = ref([])
const comments = ref([])
const currentBlog = ref(null)
const page = ref('home')
const message = ref('')
const loading = ref(false)
const query = reactive({ q: '', category: '' })
const auth = reactive({ account: '', username: '', email: '', password: '', mode: 'login' })
const editor = reactive({ title: '', intro: '', content: '', cover: '', typeId: '', isTop: false, isPrivate: false })
const commentBody = ref('')
const stats = ref(null)

const isAdmin = computed(() => user.value?.role === 'ADMIN')
const activeCategory = computed(() => categories.value.find(item => String(item.id) === String(query.category)))

function showError(error) {
  message.value = error.message || '操作失败'
  setTimeout(() => { message.value = '' }, 2600)
}

async function loadSite() {
  site.value = await api.site()
  document.title = site.value.name || 'Blogin'
}

async function loadMe() {
  user.value = await api.me()
}

async function loadBlogs() {
  loading.value = true
  try {
    const result = await api.blogs({ q: query.q, category: query.category, size: 20 })
    blogs.value = result.items
  } catch (error) {
    showError(error)
  } finally {
    loading.value = false
  }
}

async function loadCategories() {
  categories.value = await api.categories()
}

async function openBlog(blog) {
  currentBlog.value = await api.blog(blog.id)
  comments.value = await api.comments(blog.id)
  page.value = 'detail'
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

async function submitAuth() {
  try {
    user.value = auth.mode === 'login'
      ? await api.login({ account: auth.account, password: auth.password })
      : await api.register({ username: auth.username, email: auth.email, password: auth.password })
    page.value = 'home'
  } catch (error) {
    showError(error)
  }
}

async function logout() {
  await api.logout()
  user.value = null
  page.value = 'home'
}

async function submitComment() {
  if (!currentBlog.value || !commentBody.value.trim()) return
  try {
    const item = await api.comment(currentBlog.value.id, commentBody.value)
    comments.value.unshift(item)
    commentBody.value = ''
  } catch (error) {
    showError(error)
  }
}

async function openAdmin() {
  try {
    stats.value = await api.stats()
    page.value = 'admin'
  } catch (error) {
    showError(error)
  }
}

async function publishBlog() {
  try {
    await api.createBlog(editor)
    Object.assign(editor, { title: '', intro: '', content: '', cover: '', isTop: false, isPrivate: false })
    await loadBlogs()
    await openAdmin()
  } catch (error) {
    showError(error)
  }
}

async function createCategory() {
  const name = window.prompt('新分类名称')
  if (!name) return
  try {
    await api.createCategory({ name, description: '由前端管理面板创建' })
    await loadCategories()
  } catch (error) {
    showError(error)
  }
}

function sentimentText(label) {
  return { positive: '正面', neutral: '中性', negative: '负面' }[label] || '未知'
}

onMounted(async () => {
  await Promise.all([loadSite(), loadMe(), loadCategories()])
  await loadBlogs()
})
</script>

<template>
  <div class="app-shell">
    <div class="ambient-grid"></div>
    <header class="topbar">
      <button class="brand" @click="page = 'home'">
        <Sparkles :size="20" />
        <span>{{ site.name }}</span>
      </button>
      <nav>
        <button @click="page = 'home'">文章</button>
        <button v-if="isAdmin" @click="openAdmin">管理</button>
        <a v-if="site.github?.url" :href="site.github.url" target="_blank"><Github :size="18" /></a>
        <button v-if="user" class="icon-text" @click="logout"><LogOut :size="17" />退出</button>
        <button v-else class="icon-text hot" @click="page = 'auth'"><LogIn :size="17" />登录</button>
      </nav>
    </header>

    <div v-if="message" class="toast">{{ message }}</div>

    <main v-if="page === 'home'">
      <section class="hero">
        <div class="hero-copy">
          <p class="eyebrow">Flask API + Vue Interface</p>
          <h1>{{ site.heroTitle }}</h1>
          <p>{{ site.heroText }}</p>
          <div class="hero-actions">
            <button class="primary" @click="page = user ? 'home' : 'auth'">
              <UserRound :size="18" />{{ user ? user.username : '进入讨论' }}
            </button>
            <a class="ghost" :href="`mailto:${site.email}`"><Mail :size="18" />联系站长</a>
          </div>
        </div>
        <aside class="owner-panel">
          <div class="avatar">{{ (site.owner || 'U').slice(0, 1) }}</div>
          <h2>{{ site.owner }}</h2>
          <p>{{ site.subtitle }}</p>
          <dl>
            <div><dt>建站时间</dt><dd>{{ site.startDate }}</dd></div>
            <div><dt>邮箱</dt><dd>{{ site.email }}</dd></div>
            <div><dt>分类</dt><dd>{{ categories.length }}</dd></div>
          </dl>
        </aside>
      </section>

      <section class="toolbar">
        <label class="search-box">
          <Search :size="18" />
          <input v-model="query.q" placeholder="搜索文章标题、摘要或正文" @keyup.enter="loadBlogs" />
        </label>
        <select class="category-select" v-model="query.category" @change="loadBlogs">
          <option value="">全部分类</option>
          <option v-for="item in categories" :key="item.id" :value="item.id">{{ item.name }}</option>
        </select>
        <button class="filter-button" @click="loadBlogs">筛选</button>
      </section>

      <section class="section-title">
        <div>
          <p>{{ activeCategory ? activeCategory.description : 'Latest notes' }}</p>
          <h2>{{ activeCategory ? activeCategory.name : '最近文章' }}</h2>
        </div>
        <span>{{ loading ? '加载中' : `${blogs.length} 篇` }}</span>
      </section>

      <section class="blog-grid">
        <article v-for="blog in blogs" :key="blog.id" class="blog-card" @click="openBlog(blog)">
          <div class="cover" :style="{ backgroundImage: blog.cover ? `url(${blog.cover})` : '' }">
            <span>{{ blog.category }}</span>
          </div>
          <div class="card-body">
            <p>{{ blog.createdAt }}</p>
            <h3>{{ blog.title }}</h3>
            <div>{{ blog.intro }}</div>
          </div>
        </article>
      </section>
    </main>

    <main v-if="page === 'detail' && currentBlog" class="detail">
      <button class="back" @click="page = 'home'"><ArrowLeft :size="18" />返回</button>
      <article class="article">
        <p class="eyebrow">{{ currentBlog.category }} / {{ currentBlog.createdAt }}</p>
        <h1>{{ currentBlog.title }}</h1>
        <p class="intro">{{ currentBlog.intro }}</p>
        <div class="content">{{ currentBlog.content }}</div>
      </article>

      <section class="comments">
        <div class="section-title">
          <div><p>Sentiment-aware comments</p><h2>评论情感分析</h2></div>
          <span>{{ comments.length }} 条</span>
        </div>
        <div v-if="user" class="comment-editor">
          <textarea v-model="commentBody" placeholder="写下你的评论，提交后会自动分析情感倾向"></textarea>
          <button class="primary" @click="submitComment"><MessageCircle :size="18" />发布评论</button>
        </div>
        <div v-else class="login-tip">登录后即可评论，系统会自动生成情感标签。</div>
        <article v-for="comment in comments" :key="comment.id" class="comment">
          <div class="comment-head">
            <strong>{{ comment.author?.username || '匿名用户' }}</strong>
            <span>{{ comment.createdAt }}</span>
          </div>
          <p>{{ comment.body }}</p>
          <div v-if="comment.sentiment" class="sentiment" :data-label="comment.sentiment.label">
            <BarChart3 :size="16" />
            {{ sentimentText(comment.sentiment.label) }}
            <span>{{ Math.round(comment.sentiment.score * 100) }}%</span>
          </div>
        </article>
      </section>
    </main>

    <main v-if="page === 'auth'" class="auth-page">
      <section class="auth-card">
        <h1>{{ auth.mode === 'login' ? '欢迎回来' : '创建账号' }}</h1>
        <input v-if="auth.mode === 'register'" v-model="auth.username" placeholder="用户名" />
        <input v-if="auth.mode === 'register'" v-model="auth.email" placeholder="邮箱" />
        <input v-if="auth.mode === 'login'" v-model="auth.account" placeholder="邮箱或用户名" />
        <input v-model="auth.password" type="password" placeholder="密码" @keyup.enter="submitAuth" />
        <button class="primary" @click="submitAuth">{{ auth.mode === 'login' ? '登录' : '注册' }}</button>
        <button class="link" @click="auth.mode = auth.mode === 'login' ? 'register' : 'login'">
          {{ auth.mode === 'login' ? '没有账号？去注册' : '已有账号？去登录' }}
        </button>
      </section>
    </main>

    <main v-if="page === 'admin'" class="admin-page">
      <section class="stats">
        <div><span>文章</span><strong>{{ stats?.blogs || 0 }}</strong></div>
        <div><span>评论</span><strong>{{ stats?.comments || 0 }}</strong></div>
        <div><span>用户</span><strong>{{ stats?.users || 0 }}</strong></div>
        <div><span>分类</span><strong>{{ stats?.categories || 0 }}</strong></div>
      </section>
      <section class="editor">
        <div class="section-title">
          <div><p>Admin console</p><h2>发布文章</h2></div>
          <button @click="createCategory"><Plus :size="17" />新分类</button>
        </div>
        <input v-model="editor.title" placeholder="文章标题" />
        <input v-model="editor.intro" placeholder="文章摘要" />
        <input v-model="editor.cover" placeholder="封面图片 URL，可留空" />
        <select v-model="editor.typeId">
          <option value="">默认分类</option>
          <option v-for="item in categories" :key="item.id" :value="item.id">{{ item.name }}</option>
        </select>
        <textarea v-model="editor.content" placeholder="正文内容" rows="12"></textarea>
        <div class="switch-row">
          <label><input v-model="editor.isTop" type="checkbox" />置顶</label>
          <label><input v-model="editor.isPrivate" type="checkbox" />私密</label>
        </div>
        <button class="primary" @click="publishBlog"><PenLine :size="18" />发布</button>
      </section>
    </main>
  </div>
</template>
