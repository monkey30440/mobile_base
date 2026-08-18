// Copyright 2026 mobile_base contributors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#include <gtest/gtest.h>
#include <vector>

#include "mobile_base_control/m1_latency_stats.hpp"

using mobile_base_control::ErrorCode;
using mobile_base_control::LatencyStats;
using mobile_base_control::SampleRecord;

TEST(LatencyStatsTest, EmptySamples)
{
  std::vector<SampleRecord> empty;
  const auto stats = LatencyStats::compute(empty);

  EXPECT_EQ(stats.total_samples, 0u);
  EXPECT_EQ(stats.success_count, 0u);
  EXPECT_EQ(stats.failure_count, 0u);
  EXPECT_EQ(stats.timeout_count, 0u);
  EXPECT_DOUBLE_EQ(stats.min_us, 0.0);
  EXPECT_DOUBLE_EQ(stats.max_us, 0.0);
  EXPECT_DOUBLE_EQ(stats.mean_us, 0.0);
  EXPECT_DOUBLE_EQ(stats.stddev_us, 0.0);
  EXPECT_DOUBLE_EQ(stats.p50_us, 0.0);
}

TEST(LatencyStatsTest, SingleSample)
{
  std::vector<SampleRecord> samples;
  SampleRecord r;
  r.seq = 1;
  r.elapsed_us = 3500.0;
  r.ok = true;
  samples.push_back(r);

  const auto stats = LatencyStats::compute(samples);
  EXPECT_EQ(stats.total_samples, 1u);
  EXPECT_EQ(stats.success_count, 1u);
  EXPECT_EQ(stats.failure_count, 0u);
  EXPECT_DOUBLE_EQ(stats.min_us, 3500.0);
  EXPECT_DOUBLE_EQ(stats.max_us, 3500.0);
  EXPECT_DOUBLE_EQ(stats.mean_us, 3500.0);
  EXPECT_DOUBLE_EQ(stats.stddev_us, 0.0);
  EXPECT_DOUBLE_EQ(stats.p50_us, 3500.0);
  EXPECT_DOUBLE_EQ(stats.p90_us, 3500.0);
  EXPECT_DOUBLE_EQ(stats.p99_us, 3500.0);
}

TEST(LatencyStatsTest, AllFailedSamples)
{
  std::vector<SampleRecord> samples;
  for (size_t i = 0; i < 5; ++i) {
    SampleRecord r;
    r.seq = i + 1;
    r.elapsed_us = 100000.0;
    r.ok = false;
    r.error = ErrorCode::TIMEOUT;
    samples.push_back(r);
  }

  const auto stats = LatencyStats::compute(samples);
  EXPECT_EQ(stats.total_samples, 5u);
  EXPECT_EQ(stats.success_count, 0u);
  EXPECT_EQ(stats.failure_count, 5u);
  EXPECT_EQ(stats.timeout_count, 5u);
  EXPECT_DOUBLE_EQ(stats.min_us, 0.0);
  EXPECT_DOUBLE_EQ(stats.mean_us, 0.0);
}

TEST(LatencyStatsTest, MixedSuccessAndFailure)
{
  std::vector<SampleRecord> samples;

  // 3 successful samples: 2000, 4000, 6000
  for (double val : {2000.0, 4000.0, 6000.0}) {
    SampleRecord r;
    r.elapsed_us = val;
    r.ok = true;
    samples.push_back(r);
  }

  // 2 failed samples
  SampleRecord f1;
  f1.ok = false;
  f1.error = ErrorCode::TIMEOUT;
  samples.push_back(f1);

  SampleRecord f2;
  f2.ok = false;
  f2.error = ErrorCode::INVALID_RESPONSE;
  samples.push_back(f2);

  const auto stats = LatencyStats::compute(samples);
  EXPECT_EQ(stats.total_samples, 5u);
  EXPECT_EQ(stats.success_count, 3u);
  EXPECT_EQ(stats.failure_count, 2u);
  EXPECT_EQ(stats.timeout_count, 1u);

  EXPECT_DOUBLE_EQ(stats.min_us, 2000.0);
  EXPECT_DOUBLE_EQ(stats.max_us, 6000.0);
  EXPECT_DOUBLE_EQ(stats.mean_us, 4000.0);
  EXPECT_DOUBLE_EQ(stats.p50_us, 4000.0);
}

TEST(LatencyStatsTest, DeterministicPercentiles)
{
  // 100 samples uniformly spaced from 1000 us to 100000 us (step 1000)
  std::vector<SampleRecord> samples;
  for (size_t i = 1; i <= 100; ++i) {
    SampleRecord r;
    r.seq = i;
    r.elapsed_us = static_cast<double>(i * 1000);
    r.ok = true;
    samples.push_back(r);
  }

  const auto stats = LatencyStats::compute(samples);
  EXPECT_EQ(stats.total_samples, 100u);
  EXPECT_EQ(stats.success_count, 100u);
  EXPECT_DOUBLE_EQ(stats.min_us, 1000.0);
  EXPECT_DOUBLE_EQ(stats.max_us, 100000.0);
  EXPECT_DOUBLE_EQ(stats.mean_us, 50500.0);
  EXPECT_NEAR(stats.p50_us, 50500.0, 1.0);
  EXPECT_NEAR(stats.p90_us, 90100.0, 1.0);
  EXPECT_NEAR(stats.p95_us, 95050.0, 1.0);
  EXPECT_NEAR(stats.p99_us, 99010.0, 1.0);
}
