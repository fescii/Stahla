#!/usr/bin/env python3
"""Test script for the real spike analysis implementation."""

from app.models.latency.metrics.percentiles import ServiceType
from app.models.latency.analysis.spikes import LatencySpike, ServiceSpikeAnalysis
from app.services.redis.service import RedisService
from app.services.dash.latency.analysis.analyzer import LatencyAnalyzer
import asyncio
import sys
import os

# Add the app directory to the path
sys.path.insert(0, '/home/femar/A03/Stahla')


async def test_real_spike_analysis():
  """Test the real spike analysis implementation."""
  print("🔧 Testing real spike analysis implementation...")

  try:
    # Create a mock Redis service for testing
    redis_service = RedisService()
    analyzer = LatencyAnalyzer(redis_service)

    print("✅ Successfully created LatencyAnalyzer")

    # Test getting spikes for each service
    services = ["quote", "location", "gmaps", "redis"]

    for service in services:
      print(f"\n📊 Testing spike analysis for {service}...")

      try:
        # This will attempt to get real spike data
        spikes = await analyzer.get_latency_spikes(
            service_type=service,
            threshold_multiplier=3.0,
            minutes=60
        )

        print(f"   ✅ Got {len(spikes)} spikes for {service}")

        if spikes:
          print(f"   📈 Sample spike: {spikes[0]}")
        else:
          print(f"   📉 No spikes detected for {service}")

      except Exception as e:
        print(f"   ❌ Error analyzing {service}: {e}")

    print("\n🎉 Real spike analysis test completed!")

  except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback
    traceback.print_exc()


if __name__ == "__main__":
  asyncio.run(test_real_spike_analysis())
