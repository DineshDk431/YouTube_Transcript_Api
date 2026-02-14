// Three.js Starfield Background
// Theme: Cosmic Nebula (Hot Pink, Cyan, Gold)

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });

renderer.setSize(window.innerWidth, window.innerHeight);
renderer.domElement.style.position = 'fixed';
renderer.domElement.style.top = '0';
renderer.domElement.style.left = '0';
renderer.domElement.style.zIndex = '-1';
document.body.prepend(renderer.domElement);

// Particles
const particlesGeometry = new THREE.BufferGeometry();
const particlesCount = 4000;

const posArray = new Float32Array(particlesCount * 3);
const colorArray = new Float32Array(particlesCount * 3); // RGB for each particle

// Colors: Hot Pink (#ff00cc), Cyan (#33ccff), Gold (#ffd700)
const colorPalette = [
    new THREE.Color('#ff00cc'),
    new THREE.Color('#33ccff'),
    new THREE.Color('#ffd700')
];

for (let i = 0; i < particlesCount * 3; i += 3) {
    // Position
    posArray[i] = (Math.random() - 0.5) * 15;     // x
    posArray[i + 1] = (Math.random() - 0.5) * 15;   // y
    posArray[i + 2] = (Math.random() - 0.5) * 15;   // z

    // Color
    const color = colorPalette[Math.floor(Math.random() * colorPalette.length)];
    colorArray[i] = color.r;
    colorArray[i + 1] = color.g;
    colorArray[i + 2] = color.b;
}

particlesGeometry.setAttribute('position', new THREE.BufferAttribute(posArray, 3));
particlesGeometry.setAttribute('color', new THREE.BufferAttribute(colorArray, 3));

// Material
const material = new THREE.PointsMaterial({
    size: 0.015,
    vertexColors: true,
    transparent: true,
    opacity: 0.8,
    blending: THREE.AdditiveBlending
});

// Mesh
const particlesMesh = new THREE.Points(particlesGeometry, material);
scene.add(particlesMesh);

camera.position.z = 3;

// Mouse Interaction
let mouseX = 0;
let mouseY = 0;

document.addEventListener('mousemove', (event) => {
    mouseX = event.clientX / window.innerWidth - 0.5;
    mouseY = event.clientY / window.innerHeight - 0.5;
});

// Animation Loop
const clock = new THREE.Clock();

function animate() {
    requestAnimationFrame(animate);

    const elapsedTime = clock.getElapsedTime();

    // Rotate entire system slowly
    particlesMesh.rotation.y = elapsedTime * 0.05;
    particlesMesh.rotation.x = elapsedTime * 0.02;

    // Mouse parallax
    particlesMesh.rotation.y += mouseX * 0.05;
    particlesMesh.rotation.x += mouseY * 0.05;

    renderer.render(scene, camera);
}

animate();

// Resize Handler
window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});
