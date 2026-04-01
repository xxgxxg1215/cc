const api = require('../../utils/api')
Page({
    data: { posts: [], page: 1, noMore: false, loading: false },
    onShow() { this.setData({ page: 1, posts: [], noMore: false }); this.loadPosts() },
    loadPosts() {
        if (this.data.loading || this.data.noMore) return
        this.setData({ loading: true })
        api.getPosts(this.data.page).then(data => {
            const list = this.data.posts.concat(data.list || [])
            this.setData({ posts: list, loading: false, noMore: list.length >= data.total, page: this.data.page + 1 })
        }).catch(() => this.setData({ loading: false }))
    },
    onReachBottom() { this.loadPosts() },
    onTapPost(e) { wx.navigateTo({ url: '/pages/community-detail/community-detail?id=' + e.currentTarget.dataset.id }) },
    onCreatePost() { wx.navigateTo({ url: '/pages/community-post/community-post' }) }
})
