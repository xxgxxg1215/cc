const api = require('../../utils/api')
Page({
    data: { detail: null },
    onLoad(options) {
        if (options.id) {
            api.getEncyclopediaDetail(options.id).then(data => { this.setData({ detail: data }) })
        }
    }
})
