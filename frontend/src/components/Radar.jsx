import React, { useRef, useMemo, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { EffectComposer, Bloom, Scanline, Noise, Vignette } from '@react-three/postprocessing';
import * as THREE from 'three';

function Sweep() {
    const mesh = useRef();
    useFrame((state, delta) => {
        if (mesh.current) {
            mesh.current.rotation.z -= delta * 1.5;
        }
    });

    return (
        <mesh ref={mesh} rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.1, 0]}>
            <circleGeometry args={[8, 64, 0, Math.PI / 6]} />
            <meshBasicMaterial
                color="#00ff41"
                transparent
                opacity={0.15}
                side={THREE.DoubleSide}
                depthWrite={false}
                blending={THREE.AdditiveBlending}
            />
        </mesh>
    );
}

function Grid() {
    return (
        <group rotation={[-Math.PI / 2, 0, 0]}>
            <gridHelper args={[30, 30, 0x003300, 0x001100]} position={[0, -0.1, 0]} />
            {[2, 4, 6, 8].map(r => (
                <lineLoop key={r}>
                    <ringGeometry args={[r, r + 0.05, 64]} />
                    <meshBasicMaterial color="#003300" side={THREE.DoubleSide} transparent opacity={0.5} />
                </lineLoop>
            ))}
        </group>
    );
}

// Visualizes the 64 CSI subcarriers as a floating spectral grid
function SpectralGrid({ csi }) {
    const mesh = useRef();
    const dummy = useMemo(() => new THREE.Object3D(), []);

    useFrame((state) => {
        if (!mesh.current || !csi.length) return;

        const time = state.clock.getElapsedTime();

        csi.forEach((val, i) => {
            // Circle of bars
            const angle = (i / 64) * Math.PI * 2;
            const radius = 3.5;

            const x = Math.cos(angle) * radius;
            const z = Math.sin(angle) * radius;

            dummy.position.set(x, 0, z);
            dummy.rotation.y = -angle;

            // Height based on CSI amplitude
            const h = val * 2;
            dummy.scale.set(0.1, h, 0.1);
            dummy.position.y = h / 2; // Grow up from floor

            dummy.updateMatrix();
            mesh.current.setMatrixAt(i, dummy.matrix);
        });
        mesh.current.instanceMatrix.needsUpdate = true;
    });

    return (
        <instancedMesh ref={mesh} args={[null, null, 64]}>
            <boxGeometry args={[1, 1, 1]} />
            <meshBasicMaterial color="#00ff41" transparent opacity={0.5} wireframe />
        </instancedMesh>
    );
}

// OpenPose Style Skeleton
function OpenPoseSkeleton({ rssi, variance, activity, position = null, isAnimal = false, label = "" }) {
    const group = useRef();

    // Map RSSI to Distance (Z) if position not provided. 
    // -30dBm (Close) -> Z=0, -90dBm (Far) -> Z=-10
    const targetZ = position ? position[2] : Math.max(-10, Math.min(2, (rssi + 40) / 5));
    const targetX = position ? position[0] : 0;
    const targetY = position ? position[1] : -0.5;

    useFrame((state) => {
        if (!group.current) return;

        // Smoothly lerp to the target position
        group.current.position.z = THREE.MathUtils.lerp(group.current.position.z, -targetZ, 0.1);
        group.current.position.x = THREE.MathUtils.lerp(group.current.position.x, targetX, 0.1);
        group.current.position.y = THREE.MathUtils.lerp(group.current.position.y, targetY, 0.1);

        // Jitter based on signal variance (Real physics simulation)
        if (!position) {
            const jitter = Math.max(0, variance - 2) * 0.05;
            const t = state.clock.getElapsedTime();
            if (jitter > 0) {
                group.current.position.x += Math.sin(t * 10) * jitter;
                group.current.position.y += Math.cos(t * 15) * jitter;
            }
        }
    });

    // Joints for Human
    const humanJoints = [
        { pos: [0, 1.7, 0], color: 'white' },   // 0: Nose
        { pos: [0, 1.5, 0], color: 'red' },     // 1: Neck
        { pos: [-0.3, 1.5, 0], color: 'orange' }, // 2: RShoulder
        { pos: [-0.4, 1.1, 0], color: 'orange' }, // 3: RElbow
        { pos: [-0.5, 0.8, 0], color: 'orange' }, // 4: RWrist
        { pos: [0.3, 1.5, 0], color: 'cyan' },    // 5: LShoulder
        { pos: [0.4, 1.1, 0], color: 'cyan' },    // 6: LElbow
        { pos: [0.5, 0.8, 0], color: 'cyan' },    // 7: LWrist
        { pos: [0, 0.8, 0], color: 'orange' },    // 8: MidHip
        { pos: [-0.2, 0.8, 0], color: 'orange' }, // 9: RHip
        { pos: [-0.25, 0.4, 0], color: 'orange' },// 10: RKnee
        { pos: [-0.3, 0, 0], color: 'orange' },   // 11: RAnkle
        { pos: [0.2, 0.8, 0], color: 'cyan' },    // 12: LHip
        { pos: [0.25, 0.4, 0], color: 'cyan' },   // 13: LKnee
        { pos: [0.3, 0, 0], color: 'cyan' },      // 14: LAnkle
    ];

    const humanBones = [
        { start: 0, end: 1, color: 'red' },
        { start: 1, end: 2, color: 'orange' },
        { start: 2, end: 3, color: 'orange' },
        { start: 3, end: 4, color: 'orange' },
        { start: 1, end: 5, color: 'cyan' },
        { start: 5, end: 6, color: 'cyan' },
        { start: 6, end: 7, color: 'cyan' },
        { start: 1, end: 8, color: 'red' },
        { start: 8, end: 9, color: 'orange' },
        { start: 9, end: 10, color: 'yellow' },
        { start: 10, end: 11, color: 'yellow' },
        { start: 8, end: 12, color: 'cyan' },
        { start: 12, end: 13, color: 'cyan' },
        { start: 13, end: 14, color: 'cyan' },
    ];

    // Animal Representation (Diamond shape)
    const animalJoints = [
        { pos: [0, 0.5, 0], color: '#00d4ff' },  // Top
        { pos: [0.4, 0.25, 0], color: '#00d4ff' }, // Right
        { pos: [-0.4, 0.25, 0], color: '#00d4ff' }, // Left
        { pos: [0, 0, 0], color: '#00d4ff' },    // Bottom
        { pos: [0, 0.25, 0.3], color: '#00d4ff' }, // Front
    ];

    const animalBones = [
        { start: 0, end: 1, color: '#00d4ff' },
        { start: 1, end: 3, color: '#00d4ff' },
        { start: 3, end: 2, color: '#00d4ff' },
        { start: 2, end: 0, color: '#00d4ff' },
        { start: 0, end: 4, color: '#00d4ff' },
        { start: 3, end: 4, color: '#00d4ff' },
    ];

    const joints = isAnimal ? animalJoints : humanJoints;
    const bones = isAnimal ? animalBones : humanBones;

    return (
        <group ref={group}>
            {joints.map((joint, i) => (
                <mesh key={i} position={joint.pos}>
                    <sphereGeometry args={[isAnimal ? 0.03 : 0.04, 8, 8]} />
                    <meshBasicMaterial color={joint.color} />
                </mesh>
            ))}

            {bones.map((bone, i) => (
                <line key={i}>
                    <bufferGeometry>
                        <bufferAttribute
                            attach="attributes-position"
                            count={2}
                            array={new Float32Array([...joints[bone.start].pos, ...joints[bone.end].pos])}
                            itemSize={3}
                        />
                    </bufferGeometry>
                    <lineBasicMaterial color={bone.color} linewidth={2} />
                </line>
            ))}
        </group>
    );
}

function SignalVisualizer({ data }) {
    const mesh = useRef();

    useFrame((state) => {
        if (mesh.current) {
            mesh.current.rotation.y += 0.01;
            mesh.current.rotation.x += 0.01;

            const scale = 0.5 + (data.rssi + 100) / 40; // -100 -> 0.5, -40 -> 2
            mesh.current.scale.setScalar(scale);

            mesh.current.material.color.set(data.motion ? '#ff0000' : '#00ff41');
        }
    });

    return (
        <mesh ref={mesh} position={[0, 2, -3]}>
            <icosahedronGeometry args={[1, 1]} />
            <meshBasicMaterial wireframe color="#00ff41" transparent opacity={0.3} />
        </mesh>
    );
}

export default function Radar({ data }) {
    // Provide defaults if data is missing
    const radarData = data || {
        rssi: -100,
        rssi_var: 0,
        csi: [],
        activity: 'INITIALIZING',
        motion: false,
        tracking_ids: [],
        class_names: [],
        poses: []
    };

    // Calculate positions for camera-tracked entities
    // Map normalized camera X [0, 640] to 3D X [-5, 5]
    // Map bbox size to distance (Z)
    const entities = (radarData.tracking_ids || []).map((id, i) => {
        const bbox = radarData.bboxes[i];
        const className = radarData.class_names[i];
        const isAnimal = ["cat", "dog", "bird"].includes(className);

        if (!bbox) return null;

        const centerX = (bbox[0] + bbox[2]) / 2;
        const width = bbox[2] - bbox[0];

        const x3d = ((centerX / 640) * 10) - 5;
        const z3d = 8 - (width / 60); // Simple heuristic: wide is close

        return {
            id,
            className,
            isAnimal,
            position: [x3d, -0.5, z3d]
        };
    }).filter(e => e !== null);

    return (
        <Canvas camera={{ position: [0, 3, 6], fov: 60 }} style={{ background: 'transparent' }}>
            <fog attach="fog" args={['#000000', 5, 15]} />

            <Sweep />
            <Grid />
            <SignalVisualizer data={radarData} />

            {/* If we have camera entities, show them */}
            {entities.length > 0 ? entities.map(entity => (
                <OpenPoseSkeleton
                    key={entity.id}
                    position={entity.position}
                    isAnimal={entity.isAnimal}
                    label={entity.className}
                />
            )) : (
                /* Fallback to WiFi-only ghost if motion detected but no camera entities */
                radarData.motion && (
                    <OpenPoseSkeleton
                        rssi={radarData.rssi}
                        variance={radarData.rssi_var || radarData.var || 0}
                        activity={radarData.activity || 'CLEAR'}
                    />
                )
            )}

            {/* CSI Spectral Grid Visualization */}
            <SpectralGrid csi={radarData.csi || []} />

            <EffectComposer>
                <Bloom luminanceThreshold={0} luminanceSmoothing={0.9} height={300} intensity={1.5} />
                <Noise opacity={0.15} />
                <Vignette eskil={false} offset={0.1} darkness={1.1} />
            </EffectComposer>
        </Canvas>
    );
}
