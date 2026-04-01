const api = require('../../utils/api')
Page({
    data: { post: null, commentText: '' },
    onLoad(options) {
        if (options.id) {
            api.getPostDetail(options.id).then(data => { this.setData({ post: data }) })
        }
    },
    onCommentInput(e) { this.setData({ commentText: e.detail.value }) },
    onSubmitComment() {
        const text = this.data.commentText.trim()
        if (!text) return wx.showToast({ title: '请输入评论内容', icon: 'none' })
        api.createComment(this.data.post.id, text).then(() => {
            this.setData({ commentText: '' })
            wx.showToast({ title: '评论成功', icon: 'success' })
            // 刷新帖子
            api.getPostDetail(this.data.post.id).then(data => { this.setData({ post: data }) })
        })
    },
    onToggleLike() {
        api.toggleLike(this.data.post.id).then(data => {
            this.setData({ 'post.like_count': data.like_count })
        })
    }
})
