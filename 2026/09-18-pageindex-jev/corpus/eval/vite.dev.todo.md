=== ITEM vite.dev:309
path: vite.dev > Environment API > Formalizing Environments
Vite 6 formalizes the concept of Environments. Until Vite 5, there were two implicit Environments (`client`, and optionally `ssr`). The new Environment API allows users and framework authors to create as many environments as needed to map the way their apps work in production. This new capability required a big internal refactoring, but a lot of effort has been placed on backward compatibility. The initial goal of Vite 6 is to move the ecosystem to the new major as smoothly as possible, delaying the adoption of the APIs until enough users have migrated and frameworks and plugin authors have validated the new design.
=== END

=== ITEM vite.dev:200
path: vite.dev > Troubleshooting > Others > Cross drive links on Windows
If there's a cross drive links in your project on Windows, Vite may not work.

An example of cross drive links are:

* a virtual drive linked to a folder by `subst` command
* a symlink/junction to a different drive by `mklink` command (e.g. Yarn global cache)

Related issue: [#10802](https://github.com/vitejs/vite/issues/10802)
=== END

=== ITEM vite.dev:163
path: vite.dev > Server-Side Rendering (SSR) > SSR Externals
Dependencies are "externalized" from Vite's SSR transform module system by default when running SSR. This speeds up both dev and build.

If a dependency needs to be transformed by Vite's pipeline, for example, because Vite features are used untranspiled in them, they can be added to [`ssr.noExternal`](../config/ssr-options.md#ssr-noexternal).

For linked dependencies, they are not externalized by default to take advantage of Vite's HMR. If this isn't desired, for example, to test dependencies as if they aren't linked, you can add it to [`ssr.external`](../config/ssr-options.md#ssr-external).

:::warning Working with Aliases
If you have configured aliases that redirect one package to another, you may want to alias the actual `node_modules` packages instead to make it work for SSR externalized dependencies. Both [Yarn](https://classic.yarnpkg.com/en/docs/cli/add/#toc-yarn-add-alias) and [pnpm](https://pnpm.io/aliases/) support aliasing via the `npm:` prefix.
:::
=== END

=== ITEM vite.dev:303
path: vite.dev > Configuring Vite > Config Intellisense
Since Vite ships with TypeScript typings, you can leverage your IDE's intellisense with JSDoc type hints:

```js
/** @type {import('vite').UserConfig} */
export default {
  // ...
}
```

Alternatively, you can use the `defineConfig` helper which should provide intellisense without the need for JSDoc annotations:

```js
import { defineConfig } from 'vite'

export default defineConfig({
  // ...
})
```

Vite also supports TypeScript config files. You can use `vite.config.ts` with the `defineConfig` helper function above, or with the `satisfies` operator:

```ts
import type { UserConfig } from 'vite'

export default {
  // ...
} satisfies UserConfig
```
=== END

=== ITEM vite.dev:18
path: vite.dev > Project Philosophy > An Active Ecosystem
Vite evolution is a cooperation between framework and plugin maintainers, users, and the Vite team. We encourage active participation in Vite's Core development once a project adopts Vite. We work closely with the main projects in the ecosystem to minimize regressions on each release, aided by tools like [vite-ecosystem-ci](https://github.com/vitejs/vite-ecosystem-ci). It allows us to run the CI of major projects using Vite on selected PRs and gives us a clear status of how the Ecosystem would react to a release. We strive to fix regressions before they hit users and allow projects to update to the next versions as soon as they are released. If you are working with Vite, we invite you to join [Vite's Discord](https://chat.vite.dev) and get involved in the project too.

---
=== END

=== ITEM vite.dev:371
path: vite.dev > Shared Options > css.postcss
* **Type:** `string | (postcss.ProcessOptions & { plugins?: postcss.AcceptedPlugin[] })`

Inline PostCSS config or a custom directory to search PostCSS config from (default is project root).

For inline PostCSS config, it expects the same format as `postcss.config.js`. But for `plugins` property, only [array format](https://github.com/postcss/postcss-load-config/blob/main/README.md#array) can be used.

The search is done using [postcss-load-config](https://github.com/postcss/postcss-load-config) and only the supported config file names are loaded. Config files outside the workspace root (or the [project root](/guide/#index-html-and-project-root) if no workspace is found) are not searched by default. You can specify a custom path outside of the root to load the specific config file instead if needed.

Note if an inline config is provided, Vite will not search for other PostCSS config sources.
=== END

=== ITEM vite.dev:262
path: vite.dev > Plugin API > Chunk Import Map Information
:::info Experimental

This feature is experimental and may change in the future.

:::

When [`build.chunkImportMap`](/config/build-options#build-chunkimportmap) option is enabled, the import statements in the generated chunks will use a unique ID for each chunk instead of the file path.

To get the mapping from the chunk ID to the file path, you can access the import map emitted to the bundle in the `generateBundle` hook or the `writeBundle` hook. The import map has the name specified by [`build.rolldownOptions.experimental.chunkImportMap.fileName`](https://rolldown.rs/reference/InputOptions.experimental#chunkimportmap) (defaults to `importmap.json`).

```ts
function accessImportMap() {
  let config: ResolvedConfig
  return {
    name: 'access-import-map',
    configResolved(resolvedConfig) {
      config = resolvedConfig
    },
    generateBundle(options, bundle) {
      const chunkImportMap =
        config.build.rolldownOptions.experimental?.chunkImportMap
      if (chunkImportMap) {
        const importMapFilename =
          typeof chunkImportMap === 'object' && chunkImportMap.fileName
            ? chunkImportMap.fileName
            : 'importmap.json'
        const importMap = bundle[importMapFilename]! as OutputAsset
        const mapping = JSON.parse(importMap.source).imports
        console.log(mapping)
        // { "./entry.hash1.js": "./entry.hash2.js" }
      }
    },
  }
}
```
=== END

=== ITEM vite.dev:322
path: vite.dev > Environment API for Plugins > Accessing the Current Environment in Hooks
Given that there were only two Environments until Vite 6 (`client` and `ssr`), a `ssr` boolean was enough to identify the current environment in Vite APIs. Plugin Hooks received a `ssr` boolean in the last options parameter, and several APIs expected an optional last `ssr` parameter to properly associate modules to the correct environment (for example `server.moduleGraph.getModuleByUrl(url, { ssr })`).

With the advent of configurable environments, we now have a uniform way to access their options and instance in plugins. Plugin hooks now expose `this.environment` in their context, and APIs that previously expected a `ssr` boolean are now scoped to the proper environment (for example `environment.moduleGraph.getModuleByUrl(url)`).

The Vite server has a shared plugin pipeline, but when a module is processed it is always done in the context of a given environment. The `environment` instance is available in the plugin context.

A plugin could use the `environment` instance to change how a module is processed depending on the configuration for the environment (which can be accessed using `environment.config`).

```ts
  transform(code, id) {
    console.log(this.environment.config.resolve.conditions)
  }
```
=== END

=== ITEM vite.dev:473
path: vite.dev > Worker Options > worker.plugins
* **Type:** [`() => (Plugin | Plugin[])[]`](./shared-options#plugins)

Vite plugins that apply to the worker bundles. Note that [config.plugins](./shared-options#plugins) only applies to workers in dev, it should be configured here instead for build.
The function should return new plugin instances as they are used in parallel rolldown worker builds. As such, modifying `config.worker` options in the `config` hook will be ignored.
=== END

=== ITEM vite.dev:272
path: vite.dev > HMR API > `hot.dispose(cb)`
A self-accepting module or a module that expects to be accepted by others can use `hot.dispose` to clean-up any persistent side effects created by its updated copy:

```js twoslash
import 'vite/client'
// ---cut---
function setupSideEffect() {}

setupSideEffect()

if (import.meta.hot) {
  import.meta.hot.dispose((data) => {
    // cleanup side effect
  })
}
```
=== END

=== ITEM vite.dev:245
path: vite.dev > Plugin API > Vite Specific Hooks > `configureServer`
* **Type:** `(server: ViteDevServer) => (() => void) | void | Promise<(() => void) | void>`
* **Kind:** `async`, `sequential`
* **See also:** [ViteDevServer](./api-javascript#vitedevserver)
* **Scope:** [Global](/guide/api-environment-plugins#per-environment-hooks-and-global-hooks)

  Hook for configuring the dev server. The most common use case is adding custom middlewares to the internal [connect](https://github.com/senchalabs/connect) app:

  ```js
  const myPlugin = () => ({
    name: 'configure-server',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        // custom handle request...
      })
    },
  })
  ```

  **Injecting Post Middleware**

  The `configureServer` hook is called before internal middlewares are installed, so the custom middlewares will run before internal middlewares by default. If you want to inject a middleware **after** internal middlewares, you can return a function from `configureServer`, which will be called after internal middlewares are installed:

  ```js
  const myPlugin = () => ({
    name: 'configure-server',
    configureServer(server) {
      // return a post hook that is called after internal middlewares are
      // installed
      return () => {
        server.middlewares.use((req, res, next) => {
          // custom handle request...
        })
      }
    },
  })
  ```

  **Storing Server Access**

  In some cases, other plugin hooks may need access to the dev server instance (e.g. accessing the WebSocket server, the file system watcher, or the module graph). This hook can also be used to store the server instance for access in other hooks:

  ```js
  const myPlugin = () => {
    let server
    return {
      name: 'configure-server',
      configureServer(_server) {
        server = _server
      },
      transform(code, id) {
        if (server) {
          // use server...
        }
      },
    }
  }
  ```

  Note `configureServer` is not called when running the production build so your other hooks need to guard against its absence.
=== END

=== ITEM vite.dev:425
path: vite.dev > Build Options > build.rolldownOptions
* **Type:** [`RolldownOptions`](https://rolldown.rs/reference/)

Directly customize the underlying Rolldown bundle. This is the same as options that can be exported from a Rolldown config file and will be merged with Vite's internal Rolldown options. See [Rolldown options docs](https://rolldown.rs/reference/) for more details.

Instead of `build.rolldownOptions.input`, it is recommended to set the top-level [`input`](/config/shared-options#input) option, because it will be used in dev as well. If `build.rolldownOptions.input` is set, it overrides the top-level `input` option for build only.
=== END