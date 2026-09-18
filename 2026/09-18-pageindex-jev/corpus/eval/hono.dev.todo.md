=== ITEM hono.dev:8
path: hono.dev > Hono > Lightweight
**Hono is so small**. With the `hono/tiny` preset, its size is **under 14KB** when minified. There are many middleware and adapters, but they are bundled only when used. For context, the size of Express is 572KB.

```
$ npx wrangler dev --minify ./src/index.ts
 ⛅️ wrangler 2.20.0
--------------------
⬣ Listening at http://0.0.0.0:8787
- http://127.0.0.1:8787
- http://192.168.128.165:8787
Total Upload: 11.47 KiB / gzip: 4.34 KiB
```
=== END

=== ITEM hono.dev:235
path: hono.dev > Secure Headers Middleware > Setting Content-Security-Policy
```ts
const app = new Hono()
app.use(
  '/test',
  secureHeaders({
    reportingEndpoints: [
      {
        name: 'endpoint-1',
        url: 'https://example.com/reports',
      },
    ],
    // -- or alternatively
    // reportTo: [
    //   {
    //     group: 'endpoint-1',
    //     max_age: 10886400,
    //     endpoints: [{ url: 'https://example.com/reports' }],
    //   },
    // ],
    contentSecurityPolicy: {
      defaultSrc: ["'self'"],
      baseUri: ["'self'"],
      childSrc: ["'self'"],
      connectSrc: ["'self'"],
      fontSrc: ["'self'", 'https:', 'data:'],
      formAction: ["'self'"],
      frameAncestors: ["'self'"],
      frameSrc: ["'self'"],
      imgSrc: ["'self'", 'data:'],
      manifestSrc: ["'self'"],
      mediaSrc: ["'self'"],
      objectSrc: ["'none'"],
      reportTo: 'endpoint-1',
      reportUri: '/csp-report',
      sandbox: ['allow-same-origin', 'allow-scripts'],
      scriptSrc: ["'self'"],
      scriptSrcAttr: ["'none'"],
      scriptSrcElem: ["'self'"],
      styleSrc: ["'self'", 'https:', "'unsafe-inline'"],
      styleSrcAttr: ['none'],
      styleSrcElem: ["'self'", 'https:', "'unsafe-inline'"],
      upgradeInsecureRequests: [],
      workerSrc: ["'self'"],
    },
  })
)
```
=== END

=== ITEM hono.dev:604
path: hono.dev > Cloudflare Workers > Deploy from GitHub Actions
Before deploying code to Cloudflare via CI, you need a Cloudflare token. You can manage it from [User API Tokens](https://dash.cloudflare.com/profile/api-tokens).

If it's a newly created token, select the **Edit Cloudflare Workers** template. If you already have another token, make sure the token has the corresponding permissions.

then go to your GitHub repository settings dashboard: `Settings->Secrets and variables->Actions->Repository secrets`, and add a new secret with the name `CLOUDFLARE_API_TOKEN`.

then create `.github/workflows/deploy.yml` in your Hono project root folder, paste the following code:

```yml
name: Deploy

on:
  push:
    branches:
      - main

jobs:
  deploy:
    runs-on: ubuntu-latest
    name: Deploy
    steps:
      - uses: actions/checkout@v4
      - name: Deploy
        uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
```

then edit `wrangler.jsonc`, and add this code after the `compatibility_date` line.

```jsonc
"main": "src/index.ts",
"minify": true
```

Everything is ready! Now push the code and enjoy it.
=== END

=== ITEM hono.dev:118
path: hono.dev > IP Restriction Middleware > Usage
For your application running on Bun, if you want to allow access only from local, you can write it as follows. Specify the rules you want to deny in the `denyList` and the rules you want to allow in the `allowList`.

```ts
import { Hono } from 'hono'
import { getConnInfo } from 'hono/bun'
import { ipRestriction } from 'hono/ip-restriction'

const app = new Hono()

app.use(
  '*',
  ipRestriction(getConnInfo, {
    denyList: [],
    allowList: ['127.0.0.1', '::1'],
  })
)

app.get('/', (c) => c.text('Hello Hono!'))
```

Pass the `getConninfo` from the [ConnInfo helper](/docs/helpers/conninfo) appropriate for your environment as the first argument of `ipRestriction`. For example, for Deno, it would look like this:

```ts
import { getConnInfo } from 'hono/deno'
import { ipRestriction } from 'hono/ip-restriction'

//...

app.use(
  '*',
  ipRestriction(getConnInfo, {
    // ...
  })
)
```
=== END

=== ITEM hono.dev:789
path: hono.dev > Routing > Routing with hostname
It works fine if it includes a hostname.

```ts twoslash
import { Hono } from 'hono'
// ---cut---
const app = new Hono({
  getPath: (req) => req.url.replace(/^https?:\/([^?]+).*$/, '$1'),
})

app.get('/www1.example.com/hello', (c) => c.text('hello www1'))
app.get('/www2.example.com/hello', (c) => c.text('hello www2'))
```
=== END

=== ITEM hono.dev:304
path: hono.dev > css Helper > Security
The CSS helpers are CSS-authoring APIs: like other CSS-in-JS libraries, interpolated values are inserted as **raw CSS**. They block breaking out into HTML (quotes, backslashes, and `</`), but `{`, `}`, and `;` pass through since they are valid CSS.

::: warning
Treat the CSS helpers like other raw sinks (`html`, `raw`, `rawCssString`): **don't pass untrusted input into them directly.** Doing so allows CSS injection. Validate against an allowlist first.

```tsx
const ALLOWED_COLORS = ['red', 'green', 'blue']
const color = ALLOWED_COLORS.includes(input) ? input : 'black'
const headerClass = css`
  color: ${color};
`
```

:::
=== END

=== ITEM hono.dev:787
path: hono.dev > Routing > Grouping without changing base
You can also group multiple instances while keeping base.

```ts twoslash
import { Hono } from 'hono'
// ---cut---
const book = new Hono()
book.get('/book', (c) => c.text('List Books')) // GET /book
book.post('/book', (c) => c.text('Create Book')) // POST /book

const user = new Hono().basePath('/user')
user.get('/', (c) => c.text('List Users')) // GET /user
user.post('/', (c) => c.text('Create User')) // POST /user

const app = new Hono()
app.route('/', book) // Handle /book
app.route('/', user) // Handle /user
```
=== END

=== ITEM hono.dev:711
path: hono.dev > Hono Stacks > Sharing the Types
To emit an endpoint specification, export its type.

::: warning

For the RPC to infer routes correctly, all included methods must be chained, and the endpoint or app type must be inferred from a declared variable. For more, see [Best Practices for RPC](https://hono.dev/docs/guides/best-practices#if-you-want-to-use-rpc-features).

:::

```ts{1,17}
const route = app.get(
  '/hello',
  zValidator(
    'query',
    z.object({
      name: z.string(),
    })
  ),
  (c) => {
    const { name } = c.req.valid('query')
    return c.json({
      message: `Hello! ${name}`,
    })
  }
)

export type AppType = typeof route
```
=== END

=== ITEM hono.dev:589
path: hono.dev > Cloudflare Workers + Vite > Bindings
You can use Cloudflare Bindings like Variables, KV, D1, and others.
Configure them in `wrangler.jsonc`. For example, to add a Variable named `MY_NAME`:

```jsonc
{
  "$schema": "node_modules/wrangler/config-schema.json",
  "name": "my-app",
  "compatibility_date": "2025-08-03",
  "main": "./src/index.tsx",
  "vars": {
    "MY_NAME": "Hono",
  },
}
```

To generate the types for your Bindings, run the `cf-typegen` script:

::: code-group

```sh [npm]
npm run cf-typegen
```

```sh [yarn]
yarn cf-typegen
```

```sh [pnpm]
pnpm run cf-typegen
```

```sh [bun]
bun run cf-typegen
```

:::

This generates a `CloudflareBindings` interface. Pass it to `Hono` as generics:

```ts
const app = new Hono<{ Bindings: CloudflareBindings }>()
```

Then access the Bindings via `c.env`:

```tsx
app.get('/', (c) => {
  return c.render(<h1>Hello! {c.env.MY_NAME}</h1>)
})
```
=== END

=== ITEM hono.dev:365
path: hono.dev > Route Helper > `routePath()` > Using with index parameter
You can optionally pass an index parameter to get the route path at a specific position, similar to `Array.prototype.at()`.

```ts
app.all('/api/*', (c, next) => {
  return next()
})

app.get('/api/users/:id', (c) => {
  console.log(routePath(c, 0)) // '/api/*' (first matched route)
  console.log(routePath(c, -1)) // '/api/users/:id' (last matched route)
  return c.text('User details')
})
```
=== END

=== ITEM hono.dev:389
path: hono.dev > SSG Helper > Plugins > Hook Types
Plugins can use the following hooks to customize the `toSSG` process:

```ts
export type BeforeRequestHook = (req: Request) => Request | false
export type AfterResponseHook = (res: Response) => Response | false
export type AfterGenerateHook = (
  result: ToSSGResult
) => void | Promise<void>
```

- **BeforeRequestHook**: Called before processing each request. Return `false` to skip the route.
- **AfterResponseHook**: Called after receiving each response. Return `false` to skip file generation.
- **AfterGenerateHook**: Called after the entire generation process completes.
=== END

=== ITEM hono.dev:92
path: hono.dev > CORS Middleware > Usage
```ts
const app = new Hono()

// CORS should be called before the route
app.use('/api/*', cors())
app.use(
  '/api2/*',
  cors({
    origin: 'http://example.com',
    allowHeaders: ['X-Custom-Header', 'Upgrade-Insecure-Requests'],
    allowMethods: ['POST', 'GET', 'OPTIONS'],
    exposeHeaders: ['Content-Length', 'X-Kuma-Revision'],
    maxAge: 600,
    credentials: true,
  })
)

app.all('/api/abc', (c) => {
  return c.json({ success: true })
})
app.all('/api2/abc', (c) => {
  return c.json({ success: true })
})
```

Multiple origins:

```ts
app.use(
  '/api3/*',
  cors({
    origin: ['https://example.com', 'https://example.org'],
  })
)

// Or you can use "function"
app.use(
  '/api4/*',
  cors({
    // `c` is a `Context` object
    origin: (origin, c) => {
      return origin.endsWith('.example.com')
        ? origin
        : 'http://example.com'
    },
  })
)
```

Dynamic allowed methods based on origin:

```ts
app.use(
  '/api5/*',
  cors({
    origin: (origin) =>
      origin === 'https://example.com' ? origin : '*',
    // `c` is a `Context` object
    allowMethods: (origin, c) =>
      origin === 'https://example.com'
        ? ['GET', 'HEAD', 'POST', 'PATCH', 'DELETE']
        : ['GET', 'HEAD'],
  })
)
```
=== END