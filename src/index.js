// Cloudflare Worker 入口（静态资源由 [assets] 提供，此 Worker 仅作兜底）
export default {
  async fetch(request, env, ctx) {
    return new Response('Not Found', { status: 404 });
  },
};
