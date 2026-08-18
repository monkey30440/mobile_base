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

#ifndef MOBILE_BASE_CONTROL__M1_LATENCY_STATS_HPP_
#define MOBILE_BASE_CONTROL__M1_LATENCY_STATS_HPP_

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <numeric>
#include <vector>

#include "mobile_base_control/m1_driver.hpp"

namespace mobile_base_control
{

struct SampleRecord
{
  size_t seq{0};
  double elapsed_us{0.0};
  bool ok{false};
  ErrorCode error{ErrorCode::NONE};
  uint16_t driver1_alarm{0};
  int16_t driver1_rpm{0};
  uint16_t driver2_alarm{0};
  int16_t driver2_rpm{0};
};

struct LatencyStats
{
  size_t total_samples{0};
  size_t success_count{0};
  size_t failure_count{0};
  size_t timeout_count{0};

  double min_us{0.0};
  double max_us{0.0};
  double mean_us{0.0};
  double stddev_us{0.0};
  double p50_us{0.0};
  double p90_us{0.0};
  double p95_us{0.0};
  double p99_us{0.0};

  static double compute_percentile(
    const std::vector<double> & sorted_values, double percentile) noexcept
  {
    if (sorted_values.empty()) {
      return 0.0;
    }
    if (sorted_values.size() == 1 || percentile <= 0.0) {
      return sorted_values.front();
    }
    if (percentile >= 100.0) {
      return sorted_values.back();
    }

    const double rank = (percentile / 100.0) * (static_cast<double>(sorted_values.size() - 1));
    const size_t lower_idx = static_cast<size_t>(std::floor(rank));
    const size_t upper_idx = static_cast<size_t>(std::ceil(rank));
    const double weight = rank - static_cast<double>(lower_idx);

    if (lower_idx == upper_idx || upper_idx >= sorted_values.size()) {
      return sorted_values[lower_idx];
    }
    return sorted_values[lower_idx] + weight *
           (sorted_values[upper_idx] - sorted_values[lower_idx]);
  }

  static LatencyStats compute(const std::vector<SampleRecord> & samples)
  {
    LatencyStats stats;
    stats.total_samples = samples.size();

    std::vector<double> valid_latencies;
    valid_latencies.reserve(samples.size());

    for (const auto & rec : samples) {
      if (rec.ok) {
        ++stats.success_count;
        valid_latencies.push_back(rec.elapsed_us);
      } else {
        ++stats.failure_count;
        if (rec.error == ErrorCode::TIMEOUT) {
          ++stats.timeout_count;
        }
      }
    }

    if (valid_latencies.empty()) {
      return stats;
    }

    std::sort(valid_latencies.begin(), valid_latencies.end());

    stats.min_us = valid_latencies.front();
    stats.max_us = valid_latencies.back();

    const double sum = std::accumulate(valid_latencies.begin(), valid_latencies.end(), 0.0);
    stats.mean_us = sum / static_cast<double>(valid_latencies.size());

    double variance_sum = 0.0;
    for (const double val : valid_latencies) {
      const double diff = val - stats.mean_us;
      variance_sum += diff * diff;
    }
    stats.stddev_us = std::sqrt(variance_sum / static_cast<double>(valid_latencies.size()));

    stats.p50_us = compute_percentile(valid_latencies, 50.0);
    stats.p90_us = compute_percentile(valid_latencies, 90.0);
    stats.p95_us = compute_percentile(valid_latencies, 95.0);
    stats.p99_us = compute_percentile(valid_latencies, 99.0);

    return stats;
  }

  static LatencyStats compute_from_values(const std::vector<double> & values)
  {
    LatencyStats stats;
    stats.total_samples = values.size();
    stats.success_count = values.size();

    if (values.empty()) {
      return stats;
    }

    std::vector<double> sorted = values;
    std::sort(sorted.begin(), sorted.end());

    stats.min_us = sorted.front();
    stats.max_us = sorted.back();

    const double sum = std::accumulate(sorted.begin(), sorted.end(), 0.0);
    stats.mean_us = sum / static_cast<double>(sorted.size());

    double variance_sum = 0.0;
    for (const double val : sorted) {
      const double diff = val - stats.mean_us;
      variance_sum += diff * diff;
    }
    stats.stddev_us = std::sqrt(variance_sum / static_cast<double>(sorted.size()));

    stats.p50_us = compute_percentile(sorted, 50.0);
    stats.p90_us = compute_percentile(sorted, 90.0);
    stats.p95_us = compute_percentile(sorted, 95.0);
    stats.p99_us = compute_percentile(sorted, 99.0);

    return stats;
  }
};

}  // namespace mobile_base_control

#endif  // MOBILE_BASE_CONTROL__M1_LATENCY_STATS_HPP_
