import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const WIDTH = 1280;
const HEIGHT = 720;
const FPS = 30;
const DURATION_SEC = 5;
const TOTAL_FRAMES = FPS * DURATION_SEC;

const PASS = new URLSearchParams(location.search).get('pass') || 'rgb';
const IS_DEPTH = PASS === 'depth';

const renderer = new THREE.WebGLRenderer({ antialias: !IS_DEPTH, preserveDrawingBuffer: true });
renderer.setPixelRatio(1);
renderer.setSize(WIDTH, HEIGHT);
renderer.shadowMap.enabled = !IS_DEPTH;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
document.body.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(IS_DEPTH ? 0x000000 : 0xbfc9d1);

if (!IS_DEPTH) {
  scene.fog = new THREE.Fog(0xbfc9d1, 30, 120);
}

// Linear view-space depth material with skinning support (near=white, far=black).
function makeDepthMaterial({ skinning = false } = {}) {
  return new THREE.ShaderMaterial({
    defines: skinning ? { USE_SKINNING: '' } : {},
    vertexShader: `
      #include <common>
      #include <skinning_pars_vertex>
      varying float vViewZ;
      void main() {
        #include <skinbase_vertex>
        vec4 mvPosition;
        #ifdef USE_SKINNING
          #include <begin_vertex>
          #include <skinning_vertex>
          mvPosition = modelViewMatrix * vec4(transformed, 1.0);
        #else
          mvPosition = modelViewMatrix * vec4(position, 1.0);
        #endif
        vViewZ = -mvPosition.z;
        gl_Position = projectionMatrix * mvPosition;
      }
    `,
    fragmentShader: `
      varying float vViewZ;
      uniform float uNear;
      uniform float uFar;
      void main() {
        float t = clamp((vViewZ - uNear) / (uFar - uNear), 0.0, 1.0);
        float v = 1.0 - t; // near = white, far = black (VACE / ControlNet convention)
        gl_FragColor = vec4(v, v, v, 1.0);
      }
    `,
    uniforms: {
      uNear: { value: 1.0 },
      uFar: { value: 80.0 }
    },
    fog: false
  });
}

function applyDepthOverride(root) {
  root.traverse((o) => {
    if (o.isMesh || o.isSkinnedMesh) {
      o.material = makeDepthMaterial({ skinning: !!o.isSkinnedMesh });
      o.castShadow = false;
      o.receiveShadow = false;
    }
  });
}

const camera = new THREE.PerspectiveCamera(35, WIDTH / HEIGHT, 0.1, 500);

const hemi = new THREE.HemisphereLight(0xffffff, 0x556677, 0.55);
scene.add(hemi);

const sun = new THREE.DirectionalLight(0xffffff, 1.1);
sun.position.set(6, 20, 8);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
sun.shadow.camera.left = -20;
sun.shadow.camera.right = 20;
sun.shadow.camera.top = 20;
sun.shadow.camera.bottom = -20;
sun.shadow.camera.near = 1;
sun.shadow.camera.far = 60;
sun.shadow.bias = -0.0005;
scene.add(sun);

const clayMat = new THREE.MeshStandardMaterial({ color: 0xaeb2b8, roughness: 0.95, metalness: 0.0 });

// Deterministic pseudo-random (mulberry32) — Math.random forbidden in some contexts, and we want stable frames.
function rng(seed) {
  let s = seed >>> 0;
  return function () {
    s = (s + 0x6D2B79F5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Undulated ground: 200x200 with 60x60 segments, low-freq noise displacement.
const groundGeom = new THREE.PlaneGeometry(400, 400, 60, 60);
{
  const pos = groundGeom.attributes.position;
  const rnd = rng(1337);
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i);
    const y = pos.getY(i);
    const d2 = x * x + y * y;
    // Keep the near region (r < 8) fairly flat so the character isn't lifted.
    const nearFactor = Math.min(1, Math.max(0, (Math.sqrt(d2) - 6) / 20));
    const bump = (Math.sin(x * 0.07 + y * 0.11) * 0.6 + Math.cos(x * 0.13 - y * 0.05) * 0.4 + (rnd() - 0.5) * 0.4) * nearFactor;
    pos.setZ(i, bump);
  }
  pos.needsUpdate = true;
  groundGeom.computeVertexNormals();
}
const ground = new THREE.Mesh(groundGeom, clayMat.clone());
ground.rotation.x = -Math.PI / 2;
ground.receiveShadow = true;
scene.add(ground);

// Distant hills at treeline (low-poly ridge).
{
  const hillsGeom = new THREE.PlaneGeometry(300, 30, 60, 6);
  const pos = hillsGeom.attributes.position;
  const rnd = rng(4242);
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i);
    const y = pos.getY(i);
    const hRise = Math.max(0, y + 15); // higher at top edge
    const noise = Math.sin(x * 0.06) * 2 + Math.cos(x * 0.11 + 0.7) * 1.5 + Math.sin(x * 0.23) * 0.8 + (rnd() - 0.5) * 0.6;
    pos.setZ(i, noise * (hRise / 30) * 3);
  }
  pos.needsUpdate = true;
  hillsGeom.computeVertexNormals();
  const hills = new THREE.Mesh(hillsGeom, clayMat.clone());
  hills.position.set(0, 0, 55);
  hills.rotation.x = -Math.PI / 2;
  scene.add(hills);
}

// Scattered trees (cone + small cylinder trunk) around the field mid-distance.
{
  const rnd = rng(9001);
  const trunkMat = clayMat.clone();
  const crownMat = clayMat.clone();
  for (let i = 0; i < 22; i++) {
    const angle = rnd() * Math.PI * 2;
    const r = 22 + rnd() * 28;
    const x = Math.cos(angle) * r;
    const z = Math.sin(angle) * r;
    // Keep trees off the character's forward corridor.
    if (Math.abs(x) < 5 && z > -5 && z < 40) continue;
    const scale = 0.8 + rnd() * 1.4;
    const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.15 * scale, 0.2 * scale, 1.4 * scale, 16), trunkMat);
    trunk.position.set(x, 0.7 * scale, z);
    trunk.castShadow = true;
    scene.add(trunk);
    // Stack multiple cones for a fuller conifer silhouette.
    for (let k = 0; k < 3; k++) {
      const layerR = (1.3 - k * 0.28) * scale;
      const layerH = 1.4 * scale;
      const layer = new THREE.Mesh(new THREE.ConeGeometry(layerR, layerH, 24), crownMat);
      layer.position.set(x, 1.4 * scale + 0.9 * scale + k * 0.9 * scale, z);
      layer.castShadow = true;
      scene.add(layer);
    }
  }
}

// Cloud puffs: small flat puffs scattered across the sky so a tilt-up
// still finds sparse structure without filling the frame with rock-like blobs.
{
  const rnd = rng(31415);
  const cloudMat = clayMat.clone();
  // Distributed clouds: overhead sparse + mid-far layered.
  const clouds = [
    // Overhead sparse (visible when camera tilts up)
    { x: -6, y: 28, z: 15, r: 1.8 },
    { x: 5, y: 30, z: 22, r: 2.2 },
    { x: -3, y: 32, z: 32, r: 2.0 },
    { x: 9, y: 34, z: 38, r: 2.4 },
    // Mid-distance layer
    { x: -14, y: 24, z: 30, r: 2.6 },
    { x: 14, y: 26, z: 35, r: 2.8 },
    { x: -22, y: 22, z: 45, r: 2.4 },
    { x: 8, y: 30, z: 50, r: 3.0 },
    // Far horizon strip
    { x: -25, y: 18, z: 60, r: 2.8 },
    { x: 22, y: 20, z: 65, r: 3.0 },
    { x: -8, y: 20, z: 70, r: 2.6 },
    { x: 12, y: 22, z: 72, r: 2.8 },
  ];
  for (const c of clouds) {
    const group = new THREE.Group();
    const nPuffs = 8 + Math.floor(rnd() * 6);
    for (let i = 0; i < nPuffs; i++) {
      const puff = new THREE.Mesh(
        new THREE.SphereGeometry(c.r * (0.5 + rnd() * 0.6), 32, 24),
        cloudMat
      );
      puff.position.set(
        (rnd() - 0.5) * c.r * 2.8,
        (rnd() - 0.5) * c.r * 0.5,
        (rnd() - 0.5) * c.r * 2.2
      );
      const flat = 0.32 + rnd() * 0.18;
      puff.scale.set(1.5 + rnd() * 0.4, flat, 1.0 + rnd() * 0.4);
      group.add(puff);
    }
    group.position.set(c.x, c.y, c.z);
    scene.add(group);
  }
}

function buildAirplane() {
  const g = new THREE.Group();
  const bodyMat = clayMat.clone();

  const body = new THREE.Mesh(new THREE.CylinderGeometry(0.6, 0.5, 6, 24), bodyMat);
  body.rotation.z = Math.PI / 2;
  body.castShadow = true;
  g.add(body);

  const nose = new THREE.Mesh(new THREE.ConeGeometry(0.5, 1.2, 24), bodyMat);
  nose.rotation.z = -Math.PI / 2;
  nose.position.x = 3.6;
  nose.castShadow = true;
  g.add(nose);

  const tailCone = new THREE.Mesh(new THREE.ConeGeometry(0.55, 1.3, 24), bodyMat);
  tailCone.rotation.z = Math.PI / 2;
  tailCone.position.x = -3.65;
  tailCone.castShadow = true;
  g.add(tailCone);

  const wing = new THREE.Mesh(new THREE.BoxGeometry(2.6, 0.16, 10), bodyMat);
  wing.position.set(0.2, 0.05, 0);
  wing.castShadow = true;
  g.add(wing);

  const tailH = new THREE.Mesh(new THREE.BoxGeometry(1.1, 0.12, 3.4), bodyMat);
  tailH.position.set(-3.0, 0.35, 0);
  tailH.castShadow = true;
  g.add(tailH);

  const tailV = new THREE.Mesh(new THREE.BoxGeometry(1.2, 1.4, 0.12), bodyMat);
  tailV.position.set(-3.1, 1.05, 0);
  tailV.castShadow = true;
  g.add(tailV);

  // landing gear (still down, just after takeoff)
  const gearMat = clayMat.clone();
  const strutL = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 0.9, 8), gearMat);
  strutL.position.set(0.4, -0.9, -1.4);
  strutL.castShadow = true;
  g.add(strutL);
  const wheelL = new THREE.Mesh(new THREE.CylinderGeometry(0.24, 0.24, 0.18, 16), gearMat);
  wheelL.rotation.x = Math.PI / 2;
  wheelL.position.set(0.4, -1.35, -1.4);
  wheelL.castShadow = true;
  g.add(wheelL);

  const strutR = strutL.clone(); strutR.position.z = 1.4; g.add(strutR);
  const wheelR = wheelL.clone(); wheelR.position.z = 1.4; g.add(wheelR);

  const strutN = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 0.8, 8), gearMat);
  strutN.position.set(2.6, -0.85, 0);
  strutN.castShadow = true;
  g.add(strutN);
  const wheelN = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.2, 0.14, 16), gearMat);
  wheelN.rotation.x = Math.PI / 2;
  wheelN.position.set(2.6, -1.28, 0);
  wheelN.castShadow = true;
  g.add(wheelN);

  // propeller
  const spinner = new THREE.Mesh(new THREE.SphereGeometry(0.28, 16, 12), bodyMat);
  spinner.position.x = 4.25;
  spinner.castShadow = true;
  g.add(spinner);
  const propGroup = new THREE.Group();
  propGroup.position.x = 4.32;
  const blade = new THREE.Mesh(new THREE.BoxGeometry(0.08, 2.2, 0.28), bodyMat);
  const blade2 = blade.clone();
  blade2.rotation.x = Math.PI / 2;
  propGroup.add(blade, blade2);
  g.add(propGroup);
  g.userData.prop = propGroup;

  return g;
}

const airplane = buildAirplane();
scene.add(airplane);

if (IS_DEPTH) applyDepthOverride(scene);

let mixer = null;
let walkAction = null;
let soldier = null;
let ready = false;
let readyResolve;
const readyPromise = new Promise(r => (readyResolve = r));

const loader = new GLTFLoader();
loader.load('./assets/Soldier.glb', (gltf) => {
  soldier = gltf.scene;
  soldier.traverse((o) => {
    if (o.isMesh || o.isSkinnedMesh) {
      o.castShadow = !IS_DEPTH;
      o.receiveShadow = false;
      o.material = IS_DEPTH ? makeDepthMaterial({ skinning: !!o.isSkinnedMesh }) : clayMat.clone();
    }
  });
  soldier.position.set(0, 0, 0);
  soldier.rotation.y = Math.PI; // face +Z so camera behind sees back
  scene.add(soldier);

  mixer = new THREE.AnimationMixer(soldier);
  const clip = THREE.AnimationClip.findByName(gltf.animations, 'Walk') ||
               gltf.animations.find(c => /walk/i.test(c.name)) ||
               gltf.animations[1] || gltf.animations[0];
  walkAction = mixer.clipAction(clip);
  walkAction.play();

  ready = true;
  readyResolve();
});

function lerp(a, b, t) { return a + (b - a) * t; }
function smoothstep(t) { return t * t * (3 - 2 * t); }
function clamp01(t) { return Math.max(0, Math.min(1, t)); }

function setFrame(frame) {
  const t = frame / FPS;

  // character walks slowly in +Z. Soldier's Walk clip has some root motion baked;
  // we drive position ourselves to keep control, small forward speed.
  if (soldier) {
    soldier.position.set(0, 0, t * 0.9);
  }
  if (mixer && walkAction) {
    walkAction.time = t % walkAction.getClip().duration;
    mixer.update(0);
  }

  // camera choreography (5s version)
  // 0-1.8s : dolly-in
  // 1.8-2.5s : tilt up
  // 2.5-5s : hold tilted, airplane crosses
  const dollyT = smoothstep(clamp01(t / 1.8));
  const tiltT = smoothstep(clamp01((t - 1.8) / 0.7));

  const camStartZ = -18;
  const camEndZ = -3.2;
  const camZ = lerp(camStartZ, camEndZ, dollyT);
  const camY = lerp(2.4, 1.6, dollyT);
  const camX = lerp(1.8, 0.9, dollyT);

  camera.position.set(camX, camY, camZ + (soldier ? soldier.position.z * 0.6 : 0));

  const groundTarget = new THREE.Vector3(0, 1.3, (soldier ? soldier.position.z : 0));
  const skyTarget = new THREE.Vector3(0, 22, camera.position.z + 10);
  const tgt = new THREE.Vector3().lerpVectors(groundTarget, skyTarget, tiltT);
  camera.lookAt(tgt);

  // airplane: pre-enter so it is already centered when tilt-up completes at t=2.5s.
  // just-after-takeoff feel: low altitude, nose up ~10°, gear down (built-in).
  const planeStart = 1.5;
  const planeEnd = 4.0;
  const pT = clamp01((t - planeStart) / (planeEnd - planeStart));
  const planeX = lerp(-24, 24, pT);
  const planeY = lerp(5, 11, pT);
  const planeZ = camera.position.z + 6; // stays overhead relative to camera
  airplane.position.set(planeX, planeY, planeZ);
  airplane.rotation.set(0, 0, 0);
  airplane.rotation.y = 0; // flying along +X, nose (+X) forward
  airplane.rotation.z = THREE.MathUtils.degToRad(10); // pitch up (rotation around Z = pitch since long axis is X)
  if (airplane.userData.prop) {
    airplane.userData.prop.rotation.x = t * 40;
  }

  renderer.render(scene, camera);
}

window.__ready = readyPromise;
window.__setFrame = setFrame;
window.__meta = { WIDTH, HEIGHT, FPS, TOTAL_FRAMES };

// initial idle render so page isn't blank while waiting for capture
renderer.render(scene, camera);
