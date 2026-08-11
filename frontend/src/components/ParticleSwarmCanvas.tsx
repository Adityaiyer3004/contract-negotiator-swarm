"use client";

import React, { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Points, PointMaterial } from "@react-three/drei";

function ParticleSwarm({ isProcessing }: { isProcessing: boolean }) {
  const ref = useRef<any>(null);

  // Generate 5,000 3D particle positions in a sphere using native JS Math
  const spherePositions = useMemo(() => {
    const count = 5000;
    const positions = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const u = Math.random();
      const v = Math.random();
      const theta = u * 2.0 * Math.PI;
      const phi = Math.acos(2.0 * v - 1.0);
      const r = Math.cbrt(Math.random()) * 1.5;
      const sinPhi = Math.sin(phi);
      positions[i * 3] = r * sinPhi * Math.cos(theta);
      positions[i * 3 + 1] = r * sinPhi * Math.sin(theta);
      positions[i * 3 + 2] = r * Math.cos(phi);
    }
    return positions;
  }, []);

  useFrame((_, delta) => {
    if (ref.current) {
      ref.current.rotation.x -= delta / 10;
      ref.current.rotation.y -= isProcessing ? delta * 2 : delta / 15;
    }
  });

  return (
    <group rotation={[0, 0, Math.PI / 4]}>
      <Points ref={ref} positions={spherePositions} stride={3} frustumCulled={false}>
        <PointMaterial
          transparent
          color={isProcessing ? "#34d399" : "#818cf8"}
          size={0.006}
          sizeAttenuation={true}
          depthWrite={false}
        />
      </Points>
    </group>
  );
}

export default function ParticleSwarmCanvas({ isProcessing }: { isProcessing: boolean }) {
  return (
    <div className="w-full h-full min-h-screen">
      <Canvas camera={{ position: [0, 0, 1] }}>
        <ParticleSwarm isProcessing={isProcessing} />
      </Canvas>
    </div>
  );
}
