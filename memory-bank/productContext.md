# Product Context

## Problem Statement
All-hands meetings over Zoom can become monotonous and disengaging for large groups (up to 150 participants). Traditional presentations lack interactivity, leading to reduced attention and participation.

## Solution Overview
An interactive quiz game that transforms passive meetings into engaging, competitive experiences. The game features multiple question types to accommodate different interaction styles and keeps participants actively involved through real-time responses and scoring.

## Key Objectives
- **Engagement**: Provide fun, interactive activities to maintain participant attention during long meetings
- **Scalability**: Support up to 150 concurrent participants with real-time performance
- **Ease of Use**: Simple setup and operation for quiz masters, intuitive interface for participants
- **Variety**: Multiple question types to suit different content and engagement needs
- **Real-time Feedback**: Immediate response aggregation and scoring for dynamic gameplay
- **Wheel of Fortune™ Round**: Provide a unique round where participants guess a hidden phrase in a category. The phrase is revealed one letter at a time (at a set interval), with all participants and the admin seeing the board update live. Participants can make multiple full-phrase guesses at any moment during the reveal, sustaining engagement and suspense throughout the round.
- **Robust Testing**: Comprehensive load testing infrastructure to validate performance at scale
- **Admin Control**: Advanced question management and real-time analytics for quiz masters

## Target Users
- **Quiz Masters**: Meeting organizers who need to facilitate interactive sessions
- **Participants**: All meeting attendees who want to engage actively rather than passively listen

## Success Metrics
- High participation rates (>80% of participants actively responding)
- Positive feedback on engagement levels
- Smooth performance with 150 concurrent users
- Easy integration into existing Zoom workflows

## Constraints
- Must work within Zoom/web conferencing environment
- Browser-based (no app downloads required)
- Christmas-themed for holiday season deployment
- WebSocket connections for real-time, bidirectional communication
- SQLite database for development (PostgreSQL for production)

## Business Value
- Increases meeting effectiveness and retention
- Builds team camaraderie through friendly competition
- Provides data on participation and engagement for future improvements
