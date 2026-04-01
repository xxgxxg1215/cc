const api = require('../../utils/api')
Page({
    data: { news: null },
    onLoad(options) {
        if (options.id) {
            api.getNewsDetail(options.id).then(data => { this.setData({ news: data }) })
        }
    }
})
