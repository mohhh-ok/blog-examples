=== ITEM zod.dev:76
path: zod.dev > Defining schemas > Refinements > `.refine()`
{/* <Callout>
  Checks do not (in fact, cannot) change the inferred type of the schema.
  </Callout>

  ### `.refine()` */}

<Tabs groupId="lib" items={["Zod", "Zod Mini"]}>
  <Tab value="Zod">
    ```ts
    const myString = z.string().refine((val) => val.length <= 255);
    ```
  </Tab>

  <Tab value="Zod Mini">
    ```ts
    const myString = z.string().check(z.refine((val) => val.length <= 255));
    ```
  </Tab>
</Tabs>

<Callout type="warn">
  Refinement functions should never throw. Instead they should return a falsy value to signal failure. Thrown errors are not caught by Zod.
</Callout>
=== END

=== ITEM zod.dev:68
path: zod.dev > Defining schemas > Maps
```ts
const StringNumberMap = z.map(z.string(), z.number());
type StringNumberMap = z.infer<typeof StringNumberMap>; // Map<string, number>

const myMap: StringNumberMap = new Map();
myMap.set("one", 1);
myMap.set("two", 2);

StringNumberMap.parse(myMap);
```

Map schemas can be further constrained with the following utility methods.

<Tabs groupId="lib" items={["Zod", "Zod Mini"]}>
  <Tab value="Zod">
    ```ts
    z.map(z.string(), z.number()).nonempty(); // must contain at least 1 item
    z.map(z.string(), z.number()).min(5); // must contain 5 or more items
    z.map(z.string(), z.number()).max(5); // must contain 5 or fewer items
    z.map(z.string(), z.number()).size(5); // must contain 5 items exactly
    ```
  </Tab>

  <Tab value="Zod Mini">
    ```ts
    z.map(z.string(), z.number()).check(z.minSize(1)); // alias for .nonempty()
    z.map(z.string(), z.number()).check(z.minSize(5)); // must contain 5 or more items
    z.map(z.string(), z.number()).check(z.maxSize(5)); // must contain 5 or fewer items
    z.map(z.string(), z.number()).check(z.size(5)); // must contain 5 items exactly
    ```
  </Tab>
</Tabs>
=== END

=== ITEM zod.dev:243
path: zod.dev > Migration guide > `ZodError` > deprecates `.addIssue()` and `.addIssues()`
Directly push to `err.issues` array instead, if necessary.

```ts
myError.issues.push({ 
  // new issue
});
```

{/* ## `.and()` dropped

  The `.and()` method on `ZodType` has been dropped in favor of `z.intersection(A, B)`. Not only is this method rarely used, there are few good reasons to use intersections at all. The `.and()` API prevented bundlers from treeshaking `ZodIntersection`, a fairly large and complex class. 

  ```ts
  z.object({ a: z.string() }).and(z.object({ b: z.number() })); // ❌

  // use z.intersection
  z.intersection(z.object({ a: z.string() }), z.object({ b: z.number() })); // ✅
  // or .extend() when possible
  z.object({ a: z.string() }).extend(z.object({ b: z.number() })); // ✅
  ``` */}
=== END

=== ITEM zod.dev:126
path: zod.dev > Codecs > Useful codecs > `utf8ToBytes`
Converts UTF-8 strings to `Uint8Array` byte arrays.

```ts
const utf8ToBytes = z.codec(z.string(), z.instanceof(Uint8Array), {
  decode: (str) => new TextEncoder().encode(str),
  encode: (bytes) => new TextDecoder().decode(bytes),
});

utf8ToBytes.decode("Hello, 世界!");  // => Uint8Array
utf8ToBytes.encode(bytes);          // => "Hello, 世界!"
```
=== END

=== ITEM zod.dev:289
path: zod.dev > Migration guide > Internal changes > adds `ZodTransform`
Meanwhile, transforms have been moved into a dedicated `ZodTransform` class. This schema class represents an input transform; in fact, you can actually define standalone transformations now:

```ts
import * as z from "zod";

const schema = z.transform(input => String(input));

schema.parse(12); // => "12"
```

This is primarily used in conjunction with `ZodPipe`. The `.transform()` method now returns an instance of `ZodPipe`.

```ts
z.string().transform(val => val); // ZodPipe<ZodString, ZodTransform>
```
=== END

=== ITEM zod.dev:90
path: zod.dev > Defining schemas > Prefaults
In Zod, setting a *default* value will short-circuit the parsing process. If the input is `undefined`, the default value is eagerly returned. As such, the default value must be assignable to the *output type* of the schema.

```ts
const schema = z.string().transform(val => val.length).default(0);
schema.parse(undefined); // => 0
```

Sometimes, it's useful to define a *prefault* ("pre-parse default") value. If the input is `undefined`, the prefault value will be parsed instead. The parsing process is *not* short circuited. As such, the prefault value must be assignable to the *input type* of the schema.

```ts
const schema = z.string().transform(val => val.length).prefault("tuna");
schema.parse(undefined); // => 4
```

This is also useful if you want to pass some input value through some mutating refinements.

```ts
const a = z.string().trim().toUpperCase().prefault("  tuna  ");
a.parse(undefined); // => "TUNA"

const b = z.string().trim().toUpperCase().default("  tuna  ");
b.parse(undefined); // => "  tuna  "
```
=== END

=== ITEM zod.dev:70
path: zod.dev > Defining schemas > Files
To validate `File` instances:

<Tabs groupId="lib" items={["Zod", "Zod Mini"]}>
  <Tab value="Zod">
    ```ts
    const fileSchema = z.file();

    fileSchema.min(10_000); // minimum .size (bytes)
    fileSchema.max(1_000_000); // maximum .size (bytes)
    fileSchema.mime("image/png"); // MIME type
    fileSchema.mime(["image/png", "image/jpeg"]); // multiple MIME types
    ```
  </Tab>

  <Tab value="Zod Mini">
    ```ts
    const fileSchema = z.file();

    fileSchema.check(z.minSize(10_000)); // minimum .size (bytes)
    fileSchema.check(z.maxSize(1_000_000)); // maximum .size (bytes)
    fileSchema.check(z.mime("image/png")); // MIME type
    fileSchema.check(z.mime(["image/png", "image/jpeg"])); // multiple MIME types
    ```
  </Tab>
</Tabs>
=== END

=== ITEM zod.dev:123
path: zod.dev > Codecs > Useful codecs > `epochSecondsToDate`
Converts Unix timestamps (seconds since epoch) to JavaScript `Date` objects.

```ts
const epochSecondsToDate = z.codec(z.int().min(0), z.date(), {
  decode: (seconds) => new Date(seconds * 1000),
  encode: (date) => Math.floor(date.getTime() / 1000),
});

epochSecondsToDate.decode(1705314600);  // => Date object
epochSecondsToDate.encode(new Date());  // => Unix timestamp in seconds
```
=== END

=== ITEM zod.dev:77
path: zod.dev > Defining schemas > Refinements > `.refine()` > `error`
To customize the error message:

<Tabs groupId="lib" items={["Zod", "Zod Mini"]}>
  <Tab value="Zod">
    ```ts
    const myString = z.string().refine((val) => val.length > 8, { 
      error: "Too short!" 
    });
    ```
  </Tab>

  <Tab value="Zod Mini">
    ```ts
    const myString = z.string().check(
      z.refine((val) => val.length > 8, { error: "Too short!" })
    );
    ```
  </Tab>
</Tabs>

The `error` option also accepts a function that receives the issue:

<Tabs groupId="lib" items={["Zod", "Zod Mini"]}>
  <Tab value="Zod">
    ```ts
    const myString = z.string().refine((val) => val.length > 8, {
      error: (iss) => `Too short: "${iss.input}"`
    });

    myString.parse("OH NO"); // ❌ Too short: "OH NO"
    ```
  </Tab>

  <Tab value="Zod Mini">
    ```ts
    const myString = z.string().check(
      z.refine((val) => val.length > 8, { error: (iss) => `Too short: "${iss.input}"` })
    );

    z.parse(myString, "OH NO"); // ❌ Too short: "OH NO"
    ```
  </Tab>
</Tabs>
=== END

=== ITEM zod.dev:113
path: zod.dev > Codecs > How encoding works > Defaults and prefaults
Defaults and prefaults are only applied in the "forward" direction.

```ts
const stringWithDefault = z.string().default("hello");

stringWithDefault.decode(undefined); 
// => "hello"

stringWithDefault.encode(undefined); 
// => ZodError: Expected string, received undefined
```

When you attach a default value to a schema, the input becomes optional (`| undefined`) but the output does not. As such, `undefined` is not a valid input to `z.encode()` and defaults/prefaults will not be applied.
=== END

=== ITEM zod.dev:29
path: zod.dev > Defining schemas > Dates
Use `z.date()` to validate `Date` instances.

```ts
z.date().safeParse(new Date()); // success: true
z.date().safeParse("2022-01-12T06:15:00.000Z"); // success: false
```

To customize the error message:

```ts
z.date({
  error: issue => issue.input === undefined ? "Required" : "Invalid date"
});
```

Zod provides a handful of date-specific validations.

<Tabs groupId="lib" items={["Zod", "Zod Mini"]}>
  <Tab value="Zod">
    ```ts
    z.date().min(new Date("1900-01-01"), { error: "Too old!" });
    z.date().max(new Date(), { error: "Too young!" });
    ```
  </Tab>

  <Tab value="Zod Mini">
    ```ts
    z.date().check(z.minimum(new Date("1900-01-01"), { error: "Too old!" }));
    z.date().check(z.maximum(new Date(), { error: "Too young!" }));
    ```
  </Tab>
</Tabs>

<div id="zod-enums" style={{height:"0px" }} />
=== END

=== ITEM zod.dev:221
path: zod.dev > Zod Mini > When (not) to use Zod Mini > Backend development
If you are using Zod on the backend, bundle size on the scale of Zod is not meaningful. This is true even in resource-constrained environments like Lambda. [This post](https://medium.com/@adtanasa/size-is-almost-all-that-matters-for-optimizing-aws-lambda-cold-starts-cad54f65cbb) benchmarks cold start times with bundles of various sizes. Here is a subset of the results:

| Bundle size                           | Lambda cold start time   |
| ------------------------------------- | ------------------------ |
| `1kb`                                 | `171ms`                  |
| `17kb` (size of gzipped non-Mini Zod) | `171.6ms` (interpolated) |
| `128kb`                               | `176ms`                  |
| `256kb`                               | `182ms`                  |
| `512kb`                               | `279ms`                  |
| `1mb`                                 | `557ms`                  |

The minimum cold start time for a negligible `1kb` bundle is `171ms`. The next bundle size tested is `128kb`, which added only `5ms`. When gzipped, the bundle size for the entirely of regular Zod is roughly `17kb`, which would correspond to a `0.6ms` increase in startup time.
=== END