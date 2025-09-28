#!/usr/bin/env python3
"""
Automated Media Verification Script
Tests Cloudinary integration with optimization and caching verification
"""

import requests
import time
import json
import io
from PIL import Image
import tempfile
import os
from typing import Dict, Any

# Configuration
BASE_URL = "http://127.0.0.1:8000/api/v1/social-suit"
MEDIA_ENDPOINT = f"{BASE_URL}/media"

class MediaVerificationTest:
    def __init__(self):
        self.results = {
            "image_test": {},
            "video_test": {},
            "summary": {}
        }
    
    def create_sample_image(self) -> io.BytesIO:
        """Create a sample PNG image for testing"""
        img = Image.new('RGB', (800, 600), color='red')
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        return img_buffer
    
    def create_sample_video(self) -> str:
        """Create a sample video file for testing"""
        # For testing purposes, we'll use a small MP4 file
        # In a real scenario, you'd have an actual video file
        video_content = b'\x00\x00\x00\x20ftypmp42\x00\x00\x00\x00mp42isom'
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        temp_file.write(video_content)
        temp_file.close()
        return temp_file.name
    
    def upload_media(self, file_data, filename: str, media_type: str) -> Dict[str, Any]:
        """Upload media file and return response"""
        files = {'file': (filename, file_data, f'{media_type}/png' if media_type == 'image' else f'{media_type}/mp4')}
        data = {'folder': 'test_verification'}
        
        start_time = time.time()
        response = requests.post(f"{MEDIA_ENDPOINT}/upload", files=files, data=data)
        upload_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            result['upload_time'] = upload_time
            return result
        else:
            raise Exception(f"Upload failed: {response.status_code} - {response.text}")
    
    def get_optimized_urls(self, public_id: str) -> Dict[str, Any]:
        """Get optimized URLs for a media file"""
        start_time = time.time()
        response = requests.get(f"{MEDIA_ENDPOINT}/{public_id}/optimized-url")
        request_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            result['request_time'] = request_time
            result['response_headers'] = dict(response.headers)
            return result
        else:
            raise Exception(f"Get optimized URLs failed: {response.status_code} - {response.text}")
    
    def verify_optimization_params(self, urls: Dict[str, str], media_type: str) -> Dict[str, bool]:
        """Verify that URLs contain required optimization parameters"""
        verification = {
            'f_auto_present': False,
            'q_auto_present': False,
            'br_auto_present': False  # Only for video
        }
        
        # Check any URL for optimization parameters
        sample_url = next(iter(urls.values())) if urls else ""
        
        verification['f_auto_present'] = 'f_auto' in sample_url
        verification['q_auto_present'] = 'q_auto' in sample_url
        
        if media_type == 'video':
            verification['br_auto_present'] = 'br_auto' in sample_url
        
        return verification
    
    def test_image_upload(self):
        """Test image upload and optimization"""
        print("🖼️  Testing image upload...")
        
        # Create and upload sample image
        image_data = self.create_sample_image()
        upload_result = self.upload_media(image_data, "test_image.png", "image")
        
        public_id = upload_result['public_id']
        print(f"✅ Image uploaded: {public_id}")
        
        # Get optimized URLs (first request)
        first_request = self.get_optimized_urls(public_id)
        time.sleep(0.1)  # Small delay
        
        # Get optimized URLs (second request for caching test)
        second_request = self.get_optimized_urls(public_id)
        
        # Verify optimization parameters
        optimization_check = self.verify_optimization_params(
            first_request.get('optimized_urls', {}), 'image'
        )
        
        self.results['image_test'] = {
            'public_id': public_id,
            'cloudinary_url': upload_result.get('secure_url'),
            'optimized_urls': first_request.get('optimized_urls', {}),
            'first_request_time': first_request['request_time'],
            'second_request_time': second_request['request_time'],
            'optimization_check': optimization_check,
            'first_request_headers': first_request.get('response_headers', {}),
            'second_request_headers': second_request.get('response_headers', {}),
            'upload_time': upload_result['upload_time']
        }
        
        print(f"✅ Image optimization verified: f_auto={optimization_check['f_auto_present']}, q_auto={optimization_check['q_auto_present']}")
    
    def test_video_upload(self):
        """Test video upload and optimization"""
        print("🎥 Testing video upload...")
        
        try:
            # Create and upload sample video
            video_path = self.create_sample_video()
            
            with open(video_path, 'rb') as video_file:
                upload_result = self.upload_media(video_file, "test_video.mp4", "video")
            
            # Clean up temp file
            os.unlink(video_path)
            
            public_id = upload_result['public_id']
            print(f"✅ Video uploaded: {public_id}")
            
            # Get optimized URLs (first request)
            first_request = self.get_optimized_urls(public_id)
            time.sleep(0.1)  # Small delay
            
            # Get optimized URLs (second request for caching test)
            second_request = self.get_optimized_urls(public_id)
            
            # Verify optimization parameters
            optimization_check = self.verify_optimization_params(
                first_request.get('optimized_urls', {}), 'video'
            )
            
            self.results['video_test'] = {
                'public_id': public_id,
                'cloudinary_url': upload_result.get('secure_url'),
                'optimized_urls': first_request.get('optimized_urls', {}),
                'first_request_time': first_request['request_time'],
                'second_request_time': second_request['request_time'],
                'optimization_check': optimization_check,
                'first_request_headers': first_request.get('response_headers', {}),
                'second_request_headers': second_request.get('response_headers', {}),
                'upload_time': upload_result['upload_time']
            }
            
            print(f"✅ Video optimization verified: f_auto={optimization_check['f_auto_present']}, q_auto={optimization_check['q_auto_present']}, br_auto={optimization_check['br_auto_present']}")
            
        except Exception as e:
            print(f"⚠️  Video test failed: {str(e)}")
            self.results['video_test'] = {'error': str(e)}
    
    def analyze_caching(self):
        """Analyze caching behavior"""
        print("🔍 Analyzing caching behavior...")
        
        caching_analysis = {}
        
        for test_type in ['image_test', 'video_test']:
            if test_type in self.results and 'error' not in self.results[test_type]:
                test_data = self.results[test_type]
                
                # Compare request times
                time_diff = test_data['second_request_time'] - test_data['first_request_time']
                caching_detected = test_data['second_request_time'] < test_data['first_request_time'] * 0.8
                
                # Check for cache headers
                cache_headers = {}
                for header_name in ['cache-control', 'etag', 'last-modified', 'x-cache']:
                    if header_name in test_data['second_request_headers']:
                        cache_headers[header_name] = test_data['second_request_headers'][header_name]
                
                caching_analysis[test_type] = {
                    'caching_detected': caching_detected,
                    'time_improvement': time_diff,
                    'cache_headers': cache_headers
                }
        
        self.results['caching_analysis'] = caching_analysis
    
    def generate_report(self):
        """Generate final verification report"""
        print("\n" + "="*60)
        print("📊 MEDIA VERIFICATION REPORT")
        print("="*60)
        
        # Image Test Results
        if 'image_test' in self.results and 'error' not in self.results['image_test']:
            img = self.results['image_test']
            print(f"\n🖼️  IMAGE TEST RESULTS:")
            print(f"   Public ID: {img['public_id']}")
            print(f"   Upload Time: {img['upload_time']:.3f}s")
            print(f"   Cloudinary URL: {img['cloudinary_url']}")
            print(f"   Optimized URLs Count: {len(img['optimized_urls'])}")
            print(f"   First Request Time: {img['first_request_time']:.3f}s")
            print(f"   Second Request Time: {img['second_request_time']:.3f}s")
            print(f"   f_auto Present: {'✅' if img['optimization_check']['f_auto_present'] else '❌'}")
            print(f"   q_auto Present: {'✅' if img['optimization_check']['q_auto_present'] else '❌'}")
            
            # Show sample optimized URLs
            print(f"   Sample Optimized URLs:")
            for size, url in list(img['optimized_urls'].items())[:3]:
                print(f"     {size}: {url[:80]}...")
        
        # Video Test Results
        if 'video_test' in self.results:
            if 'error' in self.results['video_test']:
                print(f"\n🎥 VIDEO TEST RESULTS:")
                print(f"   Error: {self.results['video_test']['error']}")
            else:
                vid = self.results['video_test']
                print(f"\n🎥 VIDEO TEST RESULTS:")
                print(f"   Public ID: {vid['public_id']}")
                print(f"   Upload Time: {vid['upload_time']:.3f}s")
                print(f"   Cloudinary URL: {vid['cloudinary_url']}")
                print(f"   Optimized URLs Count: {len(vid['optimized_urls'])}")
                print(f"   First Request Time: {vid['first_request_time']:.3f}s")
                print(f"   Second Request Time: {vid['second_request_time']:.3f}s")
                print(f"   f_auto Present: {'✅' if vid['optimization_check']['f_auto_present'] else '❌'}")
                print(f"   q_auto Present: {'✅' if vid['optimization_check']['q_auto_present'] else '❌'}")
                print(f"   br_auto Present: {'✅' if vid['optimization_check']['br_auto_present'] else '❌'}")
        
        # Caching Analysis
        if 'caching_analysis' in self.results:
            print(f"\n🔄 CACHING ANALYSIS:")
            for test_type, analysis in self.results['caching_analysis'].items():
                test_name = "Image" if "image" in test_type else "Video"
                print(f"   {test_name} Caching Detected: {'✅' if analysis['caching_detected'] else '❌'}")
                print(f"   {test_name} Time Improvement: {analysis['time_improvement']:.3f}s")
                
                if not analysis['caching_detected'] and analysis['cache_headers']:
                    print(f"   {test_name} Cache Headers:")
                    for header, value in analysis['cache_headers'].items():
                        print(f"     {header}: {value}")
        
        print("\n" + "="*60)
        
        # Save detailed results to file
        with open('media_verification_results.json', 'w') as f:
            json.dump(self.results, f, indent=2)
        print("📄 Detailed results saved to: media_verification_results.json")
    
    def run_all_tests(self):
        """Run all verification tests"""
        print("🚀 Starting Media Verification Tests...")
        print(f"🌐 Testing against: {BASE_URL}")
        
        try:
            self.test_image_upload()
            self.test_video_upload()
            self.analyze_caching()
            self.generate_report()
            
        except Exception as e:
            print(f"❌ Test failed: {str(e)}")
            raise

if __name__ == "__main__":
    tester = MediaVerificationTest()
    tester.run_all_tests()