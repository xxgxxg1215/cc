/**
 * API 请求封装（云端版）
 */
const app = getApp()

/**
 * 通用 GET 请求
 */
function get(path, data) {
  return new Promise((resolve, reject) => {
    const params = Object.assign({}, data || {})
    if (app.globalData.token) {
      params.token = app.globalData.token
    }
    wx.request({
      url: app.globalData.apiBase + path,
      method: 'GET',
      data: params,
      success(res) {
        if (res.statusCode === 200) {
          resolve(res.data)
        } else {
          reject(new Error('请求失败: ' + res.statusCode))
        }
      },
      fail(err) {
        reject(new Error('网络请求失败'))
      }
    })
  })
}

/**
 * 通用 POST 请求
 */
function post(path, data) {
  return new Promise((resolve, reject) => {
    app.getToken(token => {
      let url = app.globalData.apiBase + path
      if (token) {
        url += (url.indexOf('?') > -1 ? '&' : '?') + 'token=' + token
      }
      wx.request({
        url: url,
        method: 'POST',
        header: { 'Content-Type': 'application/json' },
        data: data || {},
        success(res) {
          if (res.statusCode === 200) {
            resolve(res.data)
          } else {
            reject(new Error('请求失败: ' + res.statusCode))
          }
        },
        fail(err) {
          reject(new Error('网络请求失败'))
        }
      })
    })
  })
}

/**
 * 通用 DELETE 请求
 */
function del(path) {
  return new Promise((resolve, reject) => {
    app.getToken(token => {
      let url = app.globalData.apiBase + path
      if (token) {
        url += (url.indexOf('?') > -1 ? '&' : '?') + 'token=' + token
      }
      wx.request({
        url: url,
        method: 'DELETE',
        success(res) {
          if (res.statusCode === 200) {
            resolve(res.data)
          } else {
            reject(new Error('请求失败: ' + res.statusCode))
          }
        },
        fail() { reject(new Error('网络请求失败')) }
      })
    })
  })
}

/**
 * 上传图片进行病害识别
 */
function predict(filePath) {
  return new Promise((resolve, reject) => {
    wx.showLoading({ title: '识别中...', mask: true })

    let url = app.globalData.apiBase + '/predict'
    const formData = {}
    if (app.globalData.token && app.globalData.userInfo) {
      formData.user_id = app.globalData.userInfo.id
    }

    wx.uploadFile({
      url: url,
      filePath: filePath,
      name: 'file',
      formData: formData,
      success(res) {
        wx.hideLoading()
        if (res.statusCode === 200) {
          try {
            const data = JSON.parse(res.data)
            resolve(data)
          } catch (e) {
            reject(new Error('服务器响应格式错误'))
          }
        } else {
          reject(new Error('识别失败，状态码: ' + res.statusCode))
        }
      },
      fail(err) {
        wx.hideLoading()
        reject(new Error('网络请求失败，请检查网络连接'))
      }
    })
  })
}

// ── 历史记录 ──
function getHistory(page, pageSize) {
  return get('/api/history/list', { page: page || 1, page_size: pageSize || 20 })
}

function deleteHistory(id) {
  return del('/api/history/' + id)
}

function clearHistory() {
  return del('/api/history/')
}

// ── 百科 ──
function getCrops() {
  return get('/api/encyclopedia/crops')
}

function getEncyclopediaList(crop, keyword) {
  return get('/api/encyclopedia/list', { crop: crop || '', keyword: keyword || '' })
}

function getEncyclopediaDetail(id) {
  return get('/api/encyclopedia/detail/' + id)
}

// ── 社区 ──
function getPosts(page) {
  return get('/api/community/posts', { page: page || 1 })
}

function getPostDetail(id) {
  return get('/api/community/posts/' + id)
}

function createPost(data) {
  return post('/api/community/posts', data)
}

function createComment(postId, content) {
  return post('/api/community/posts/' + postId + '/comments', { content: content })
}

function toggleLike(postId) {
  return post('/api/community/posts/' + postId + '/like')
}

// ── 天气 ──
function getWeather(lat, lon) {
  return get('/api/weather/now', { lat: lat, lon: lon })
}

// ── 资讯 ──
function getNewsList(page) {
  return get('/api/news/list', { page: page || 1 })
}

function getNewsDetail(id) {
  return get('/api/news/detail/' + id)
}

// ── 用户 ──
function getUserProfile() {
  return get('/api/user/profile')
}

// ── AI 聊天助手 ──
function chatMessage(message) {
  return post('/chat/message', { message: message })
}

module.exports = {
  get, post, del,
  predict,
  getHistory, deleteHistory, clearHistory,
  getCrops, getEncyclopediaList, getEncyclopediaDetail,
  getPosts, getPostDetail, createPost, createComment, toggleLike,
  getWeather,
  getNewsList, getNewsDetail,
  getUserProfile,
  chatMessage,
}
