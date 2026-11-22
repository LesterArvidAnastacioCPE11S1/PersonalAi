# Roblox Luau usage guide

## Script types and services

- `Script` runs on the server; `LocalScript` runs on the client; `ModuleScript` returns one value and must be required with `require`.
- A `Script` with `RunContext = Client` behaves like a LocalScript inside ReplicatedStorage; `RunContext = Server` runs on the server without a BaseScript location restriction.
- Get services once at the top of a script: `local Players = game:GetService("Players")`.
- Never index `game.Players.LocalPlayer` on the server; it is nil there.
- `Instance:WaitForChild(name, timeout)` returns nil after the timeout instead of yielding forever.
- Use `FindFirstChild(name, recursive)` when an object may be missing; direct indexing errors.

## Modern task scheduling

- `task.wait(seconds)` yields and returns the actual elapsed time.
- `task.spawn(func, ...)` starts a function or coroutine immediately through the scheduler; arguments after the function are passed to it.
- `task.defer(func, ...)` runs the function at the end of the current resumption cycle.
- `task.delay(seconds, func, ...)` runs the function after a delay; `task.cancel(thread)` cancels a scheduled thread.
- Deprecated: `wait`, `spawn`, `delay`. Replace them with the `task` equivalents.
- `task.wait()` with no argument waits one frame.

## Building instances

- `Instance.new("Part")` then set properties, and assign `Parent` last; the legacy second `Parent` argument is discouraged.
- `Instance:Clone()` copies an instance; set `Archivable = false` to keep runtime-only objects out of saves.
- `Instance:Destroy()` disconnects its connections and removes descendants.
- Model teleport: `Model:PivotTo(CFrame)` and `Model:GetPivot()`; for a character use `character:PivotTo(cframe)` or set `HumanoidRootPart.CFrame`.
- Attributes: `instance:SetAttribute(name, value)`, `GetAttribute`, `GetAttributes`, and `GetAttributeChangedSignal(name)`.
- CollectionService tags: `CollectionService:AddTag`, `GetTagged`, `GetInstanceAddedSignal`, `GetInstanceRemovedSignal`.

## Events and remotes

- `RemoteEvent:FireClient(player, ...)`, `FireAllClients(...)`, `FireServer(...)`; server listeners use `OnServerEvent(player, ...)`, client listeners use `OnClientEvent(...)`.
- `RemoteFunction:InvokeServer`/`InvokeClient` yields until the other side returns a value; avoid calling clients from the server for anything latency-sensitive.
- `UnreliableRemoteEvent` is for high-frequency state that can drop packets.
- Always validate remote arguments on the server: check types, distances, cooldowns, and ownership before acting.
- `BindableEvent` connects two scripts in the same context; it is not a client-server channel.
- Disconnect with `connection:Disconnect()` when an object is destroyed or a handler is replaced; prefer `RBXScriptSignal:Once` for one-shot handlers.

## Tweens and animation

- `TweenService:Create(instance, TweenInfo.new(time, easingStyle, easingDirection, repeatCount, reverses, delayTime), {Property = target})` returns a `Tween`; call `Play`, and listen to `Completed`.
- Tweenable property values include numbers, booleans, `CFrame`, `Color3`, `UDim`, `UDim2`, `Vector2`, `Vector3`, and `EnumItem`.
- `Animator:LoadAnimation(animation)` produces an `AnimationTrack`; call `Play()`, `Stop()`, and read `IsPlaying`.
- `Humanoid:LoadAnimation` is deprecated; always load through the character's `Animator`.
- RunService loops: `Heartbeat` (server and client), `Stepped` (physics step), `RenderStepped` (client, render step). Prefer events over manual polling.

## Tweening a part

```lua
local TweenService = game:GetService("TweenService")

local part = workspace:WaitForChild("Door")
local info = TweenInfo.new(1, Enum.EasingStyle.Quad, Enum.EasingDirection.Out)
local goal = { CFrame = part.CFrame * CFrame.new(0, 5, 0) }
local tween = TweenService:Create(part, info, goal)

tween:Play()
tween.Completed:Wait()
```

- `TweenService:Create` interpolates any writable properties whose types support it, such as `CFrame`, `Vector3`, `Color3`, `number`, and `UDim2`.
- Keep a reference to the tween, or the game may collect it mid-run.
- `tween.Completed:Wait()` yields until the tween finishes; `tween:Cancel()` stops it at the current value.
- If another tween targets the same property, the newer tween replaces the older one.

## Teleporting a player or model

```lua
local function teleport(player, position)
    local character = player.Character

    if not character then
        return
    end

    local root = character:FindFirstChild("HumanoidRootPart")

    if not root then
        return
    end

    character:PivotTo(CFrame.new(position))
end
```

- `Model:PivotTo(cframe)` moves a character or model in one call; `root.CFrame = CFrame.new(position)` also works but skips other parts until the next physics step.
- Run teleports on the server; call `root:SetNetworkOwner(nil)` when server authority matters.
- Wait for `HumanoidRootPart` to exist after `CharacterAdded` before teleporting.

## CFrame and vectors

- `CFrame.new(position)` keeps identity rotation; `CFrame.new(position, lookAt)` aims the -Z axis (LookVector) at a point.
- `CFrame.lookAt(position, target, upVector)` is the explicit aiming constructor; use it for cameras and projectiles.
- `CFrame * CFrame` composes; `CFrame:ToWorldSpace`, `:ToObjectSpace`, `:Lerp`, `:PointToWorldSpace`, `:VectorToWorldSpace`.
- `part.CFrame * Vector3.new(0, 0, -2)` offsets in local space; `part.CFrame.Position` is world position.
- `Vector3.Unit`, `:Cross`, `:Dot`, `:Lerp`, `:Unit`, `:Magnitude`, and `Vector3.new(x, y, z)` cover most math.
- `CFrame:ToEulerAnglesYXZ()` returns YXZ angles; `CFrame.Angles(radiansX, radiansY, radiansZ)` builds a rotation.

## Raycasting and spatial queries

- `workspace:Raycast(origin, direction, raycastParams)` returns a `RaycastResult` or nil; hit fields include `Instance`, `Position`, `Normal`, `Distance`, and `Material`.
- Build params with `RaycastParams.new()`; set `ExcludeInstances` and `IncludeInstances` to filter candidates (the older `FilterDescendantsInstances` and `FilterType` still run but are superseded), plus `IgnoreWater`, `CollisionGroup`, and `BruteForceAllSlow`.
- `workspace:GetPartBoundsInBox(cframe, size, overlapParams)` and `GetPartBoundsInRadius(position, radius, overlapParams)` return parts; `GetPartsInPart(part, overlapParams)` tests one part.
- `OverlapParams.new()` mirrors `RaycastParams` for the overlap queries.
- The legacy `workspace:FindPartOnRay` family is deprecated; use `workspace:Raycast`.

## Making a part float or hover

```lua
local part = workspace:WaitForChild("Platform")
part.Anchored = false

local attachment = Instance.new("Attachment")
attachment.Parent = part

local force = Instance.new("VectorForce")
force.Attachment0 = attachment
force.RelativeTo = Enum.ActuatorRelativeTo.World
force.ApplyAtCenterOfMass = true
force.Force = Vector3.new(0, part.AssemblyMass * workspace.Gravity, 0)
force.Parent = part
```

- The force cancels gravity, so the part floats in place until something pushes it.
- For a stable hover that resists bumps, use `AlignPosition` with one `Attachment` and a fixed target position, and raise `MaxForce`.
- `AlignOrientation` keeps the part upright while it moves.
- Set `Anchored = true` instead when the part never needs to move; physics forces do nothing on anchored parts.

## Physics

- `BasePart:ApplyImpulse(vector)` adds velocity instantly; `VectorForce`, `LinearVelocity`, and `AlignPosition` constrain motion continuously.
- `WeldConstraint` joins two parts rigidly after positioning; `Motor6D` drives articulated rigs; `HingeConstraint` and `BallSocketConstraint` limit motion.
- `part:SetNetworkOwner(nil)` gives physics ownership to the server; always set ownership explicitly for server-driven objects.
- Set `CanCollide`, `Massless`, and `CanTouch` deliberately; many physics bugs come from unintended collisions.

## Data persistence and HTTP

- `DataStoreService:GetDataStore(name)`; use `GetAsync`, `SetAsync`, `UpdateAsync`, and `RemoveAsync`.
- Wrap every DataStore call in `pcall`; retry with backoff, and check `GetRequestBudgetForRequestType`.
- `UpdateAsync` receives the current value and returns the new value; use it for read-modify-write to avoid races.
- `HttpService:JSONEncode` and `JSONDecode` convert tables; HTTP requests require the HttpEnabled game setting.
- Colored text via `RichText` uses `<font color="#RRGGBB">`; avoid user-supplied tags without sanitizing.

## Client and server rules

- The client owns input, camera, and local prediction; the server owns truth. Never trust values sent from the client.
- Keep remote payloads small and validated; reject malformed types and out-of-range numbers on the server.
- `UserInputService`, `ContextActionService`, `Camera`, and most GUI APIs are client-only.
- `Player.CharacterAdded` fires on the server with the new character model; wait for `HumanoidRootPart` before teleporting.
- Streaming: with `Workspace.StreamingEnabled`, distant instances do not exist on the client; use `WaitForChild` and handle streaming events.

## Performance

- Cache services and frequently used instances in local variables; avoid `FindFirstChild` inside loops.
- Reuse tables and instances instead of allocating per frame; object pools help for projectile and effect systems.
- Prefer event-driven code over polling in Stepped/Heartbeat.
- Use `--!strict` and typed annotations to catch nil and type mistakes early.
- Profile before optimizing: micro-optimizing cold code rarely helps, while per-frame allocations and unnecessary physics steps usually dominate.

## Typed Luau

- Add `--!strict` at the top of a script for strict type checking.
- Annotate parameters and returns: `local function damage(target: Model, amount: number): number`.
- `type` and `export type` define aliases; generics use `<T>`; `typeof(value)` derives a type from a runtime value.
- Optional values use `T?`; use `if x then` or `assert` to narrow nil before use.
- Casts use `::` (for example `(instance :: Part)`) when the type system cannot infer an `Instance` subclass.
