=== ITEM elysiajs.com:287
path: elysiajs.com > Handler&#x20; > Server Sent Events (SSE)
Elysia supports [Server Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events) by providing a `sse` utility function.

```typescript
import { Elysia, sse } from 'elysia'

new Elysia()
	.get('/sse', function* () {
		yield sse('hello world')
		yield sse({
			event: 'message',
			data: {
				message: 'This is a message',
				timestamp: new Date().toISOString()
			},
		})
	})
```

When a value is wrapped in `sse`, Elysia will automatically set the response headers to `text/event-stream` and format the data as an SSE event.
=== END

=== ITEM elysiajs.com:798
path: elysiajs.com > WebSocket > ws
Create a websocket handler

Example:

```typescript
import { Elysia } from 'elysia'

const app = new Elysia()
    .ws('/ws', {
        message(ws, message) {
            ws.send(message)
        }
    })
    .listen(3000)
```

Type:

```typescript
.ws(endpoint: path, options: Partial<WebSocketHandler<Context>>): this
```

* **endpoint** - A path to be exposed as websocket handler
* **options** - Customize WebSocket handler behavior
=== END

=== ITEM elysiajs.com:505
path: elysiajs.com > OpenAPI&#x20; > Models
By using [reference model](/essential/validation.html#reference-model), Elysia will handle the schema generation automatically.

By separating models into a dedicated section and linked by reference.

```typescript
new Elysia()
    .model({
        User: t.Object({
            id: t.Number(),
            username: t.String()
        })
    })
    .get('/user', () => ({ id: 1, username: 'saltyaom' }), {
        response: {
            200: 'User'
        },
        detail: {
            tags: ['User']
        }
    })
```
=== END

=== ITEM elysiajs.com:159
path: elysiajs.com > Eden Fetch > Error Handling
You can handle errors the same way as Eden Treaty:

```typescript
import { edenFetch } from '@elysia/eden'
import type { App } from './server'

const fetch = edenFetch<App>('http://localhost:3000')

// response type: { id: 1895, name: 'Skadi' }
const { data: nendoroid, error } = await fetch('/mirror', {
    method: 'POST',
    body: {
        id: 1895,
        name: 'Skadi'
    }
})

if(error) {
    switch(error.status) {
        case 400:
        case 401:
            throw error.value
            break

        case 500:
        case 502:
            throw error.value
            break

        default:
            throw error.value
            break
    }
}

const { id, name } = nendoroid
```
=== END

=== ITEM elysiajs.com:310
path: elysiajs.com > Integration with AI SDK > Server-Sent Events
Elysia also supports Server-Sent Events for streaming responses by simply wrapping a `ReadableStream` with the `sse` function.

```ts
import { Elysia, sse } from 'elysia' // [!code ++]
import { streamText } from 'ai'
import { openai } from '@ai-sdk/openai'

new Elysia().get('/', () => {
    const stream = streamText({
        model: openai('gpt-5'),
        system: 'You are Yae Miko from Genshin Impact',
        prompt: 'Hi! How are you doing?'
    })

    // Each chunk will be sent as a Server Sent Event
    return sse(stream.textStream) // [!code ++]

    // UI Message Stream is also supported
    return sse(stream.toUIMessageStream()) // [!code ++]
})
```
=== END

=== ITEM elysiajs.com:733
path: elysiajs.com > TypeBox (Elysia.t) > Boolean to BooleanString
Similar to [Number to Numeric](#number-to-numeric)

Any `t.Boolean` will be converted to `t.BooleanString`.

```ts
import { Elysia, t } from 'elysia'

new Elysia()
	.get('/:id', ({ id }) => id, {
		params: t.Object({
			// Converted to t.Boolean()
			id: t.Boolean()
		}),
		body: t.Object({
			// NOT converted to t.Boolean()
			id: t.Boolean()
		})
	})

// NOT converted to t.BooleanString()
t.Boolean()
```

---
=== END

=== ITEM elysiajs.com:488
path: elysiajs.com > OpenAPI > Type Gen > Browser Environment
Unfortunately, this feature requires the **fs** module to read your source code, and is not available in this web playground. As Elysia is running directly in your browser (not a separated server).

You can try this feature locally with Type Gen Example repository:

```bash
git clone https://github.com/SaltyAom/elysia-typegen-example && \
cd elysia-typegen-example && \
bun install && \
bun run dev
```
=== END

=== ITEM elysiajs.com:784
path: elysiajs.com > Validation&#x20; > Reference Model > Naming Convention
Duplicate model names will cause Elysia to throw an error. To prevent declaring duplicate model names, we can use the following naming convention.

Let's say that we have all models stored at `models/<name>.ts` and declare the prefix of the model as a namespace.

```typescript
import { Elysia, t } from 'elysia'

// admin.model.ts
export const adminModels = new Elysia()
    .model({
        'admin.auth': t.Object({
            username: t.String(),
            password: t.String()
        })
    })

// user.model.ts
export const userModels = new Elysia()
    .model({
        'user.auth': t.Object({
            username: t.String(),
            password: t.String()
        })
    })
```

This can prevent naming duplication to some extent, but ultimately, it's best to let your team decide on the naming convention.

Elysia provides an opinionated option to help prevent decision fatigue.
=== END

=== ITEM elysiajs.com:705
path: elysiajs.com > TypeBox (Elysia.t) > Primitive Type
The TypeBox API is designed around and is similar to TypeScript types.

There are many familiar names and behaviors that intersect with TypeScript counterparts, such as **String**, **Number**, **Boolean**, and **Object**, as well as more advanced features like **Intersect**, **KeyOf**, and **Tuple** for versatility.

If you are familiar with TypeScript, creating a TypeBox schema behaves the same as writing a TypeScript type, except it provides actual type validation at runtime.

To create your first schema, import **Elysia.t** from Elysia and start with the most basic type:

```typescript
import { Elysia, t } from 'elysia'

new Elysia()
	.post('/', ({ body }) => `Hello ${body}`, {
		body: t.String()
	})
	.listen(3000)
```

This code tells Elysia to validate an incoming HTTP body, ensuring that the body is a string. If it is a string, it will be allowed to flow through the request pipeline and handler.

If the shape doesn't match, it will throw an error into the [Error Life Cycle](/essential/life-cycle.html#on-error).

![Elysia Life Cycle](/assets/lifecycle-chart.svg)
=== END

=== ITEM elysiajs.com:113
path: elysiajs.com > Cookie > Assignment
Let's create a simple counter that tracks how many times you have visited the site.

\<template #answer>

1. We can update the cookie value by modifying `visit.value`.
2. We can set **HTTP only** attribute by setting `visit.httpOnly = true`.

```typescript
import { Elysia, t } from 'elysia'

new Elysia()
	.get('/', ({ cookie: { visit } }) => {
		visit.value ??= 0
		visit.value++

		visit.httpOnly = true

		return `You have visited ${visit.value} times`
	}, {
		cookie: t.Object({
			visit: t.Optional(
				t.Number()
			)
		})
	})
	.listen(3000)
```

---
=== END

=== ITEM elysiajs.com:487
path: elysiajs.com > OpenAPI > Type Gen
OpenAPI Type Gen can document your API **without manual annotation** infers directly from TypeScript type. No Zod, TypeBox, manual interface declaraiont, etc.

**This feature is unique to Elysia**, and is not available in other JavaScript frameworks.

For example, if you use Drizzle ORM or Prisma, Elysia can infer the schema directly from the query.

![Drizzle](/blog/openapi-type-gen/drizzle-typegen.webp)

> Returning Drizzle query from Elysia route handler will be automatically inferred into OpenAPI schema.

To use OpenAPI Type Gen, simply apply the `fromTypes` plugin before `openapi` plugin.

```typescript
import { Elysia } from 'elysia'

import { openapi, fromTypes } from '@elysia/openapi' // [!code ++]

new Elysia()
	.use(openapi({
		references: fromTypes() // [!code ++]
	}))
	.get('/', { hello: 'world' })
	.listen(3000)
```
=== END

=== ITEM elysiajs.com:30
path: elysiajs.com > Best Practice > Model > ✅ Do: Use Elysia's validation system
Elysia's strength is prioritizing a single source of truth for both types and runtime validation.

Instead of declaring an interface, reuse validation's model instead:

```typescript twoslash
// ✅ Do
import { Elysia, t, type UnwrapSchema } from 'elysia'

export const models = {
	customBody: t.Object({
		username: t.String(),
		password: t.String()
	})
}

// Optional if you want to extract the type from the model
type CustomBody = UnwrapSchema<typeof models.customBody>
//    ^?






// Or make the entire object as type
type Models = {
	[k in keyof typeof models]: UnwrapSchema<typeof models[k]>
}

// ❌ Don't: declare model and type separately
interface ICustomBody {
	username: string
	password: string
}
```

We can get type of model by using `typeof` with `.static` property from the model.

Then you can use the `CustomBody` type to infer the type of the request body.

```typescript twoslash
import { Elysia, t } from 'elysia'

const models = {
	customBody: t.Object({
		username: t.String(),
		password: t.String()
	})	
}
// ---cut---
// ✅ Do
new Elysia()
	.post('/login', ({ body }) => {
	                 // ^?
		return body
	}, {
		body: models.customBody
	})
```
=== END