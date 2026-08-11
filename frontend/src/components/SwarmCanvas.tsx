"use client";

import React, { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";

interface SwarmCanvasProps {
  swarmState: "IDLE" | "INGESTING" | "PAUSED_FOR_HUMAN" | "COMPLETED" | "REJECTED" | "ERROR";
}

function ParticleSwarm({ swarmState }: SwarmCanvasProps) {
  const pointsRef = useRef<THREE.Points>(null);
  const count = 1500;

  // Generate 3D sphere point cloud positions
  const [positions, colors] = useMemo(() => {
    const pos = new Float32Array(count * 3);
    const col = new Float32Array(count * 3);

    const color1 = new THREE.Color("#6366f1"); // Indigo
    const color2 = new THREE.Color("#10b981"); // Emerald

    for (let i = 0; i < count; i++) {
      const radius = 6 + Math.random() * 6;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(Math.random() * 2 - 1);

      pos[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
      pos[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
      pos[i * 3 + 2] = radius * Math.cos(phi);

      const mixedColor = color1.clone().lerp(color2, Math.random());
      col[i * 3] = mixedColor.r;
      col[i * 3 + 1] = mixedColor.g;
      col[i * 3 + 2] = mixedColor.b;
    }

    return [pos, col];
  }, []);

  useFrame((state, delta) => {
    if (!pointsRef.current) return;

    let rotSpeed = 0.15;
    if (swarmState === "INGESTING") rotSpeed = 0.8;
    if (swarmState === "COMPLETED") rotSpeed = 0.5;

    pointsRef.current.rotation.y += delta * rotSpeed;
    pointsRef.current.rotation.x += delta * (rotSpeed * 0.5);
  });

  const particleColor = useMemo(() => {
    if (swarmState === "INGESTING") return "#06b6d4"; // Cyan surge
    if (swarmState === "COMPLETED") return "#10b981"; // Toxic Emerald
    if (swarmState === "REJECTED") return "#f43f5e"; // Rose Red
    return "#818cf8"; // Deep Indigo
  }, [swarmState]);

  return (
    <group>
      <points ref={pointsRef}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            args={[positions, 3]}
          />
          <bufferAttribute
            attach="attributes-color"
            args={[colors, 3]}
          />
        </bufferGeometry>
        <pointsMaterial
          size={0.06}
          color={particleColor}
          transparent
          opacity={0.75}
          blending={THREE.AdditiveBlending}
          sizeAttenuation
        />
      </points>
    </group>
  );
}

export default function SwarmCanvas({ swarmState }: SwarmCanvasProps) {
  return (
    <div className="absolute inset-0 w-full h-full pointer-events-none z-0">
      <Canvas
        camera={{ position: [0, 0, 14], fov: 60 }}
        gl={{ antialias: true, alpha: true }}
      >
        <ambientLight intensity={0.4} />
        <pointLight position={[10, 10, 10]} intensity={1.5} color="#818cf8" />
        <pointLight position={[-10, -10, -10]} intensity={1.0} color="#10b981" />
        <ParticleSwarm swarmState={swarmState} />
      </Canvas>
    </div>
  );
}
