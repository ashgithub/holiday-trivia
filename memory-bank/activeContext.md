# Active Context

## Current Work Focus
The All-Hands Quiz Game is now production-ready with comprehensive features, robust testing infrastructure, and full scalability to 150 concurrent users. The system includes time-based scoring, enhanced participant experience, refactored admin interface, and comprehensive load testing capabilities.

## Immediate Priorities
1. **Production Deployment**: Prepare for cloud deployment with proper configuration
2. **Performance Monitoring**: Set up production monitoring and alerting
3. **User Feedback Integration**: Collect and analyze real-world usage data
4. **Advanced Scoring**: Implement word cloud similarity-based scoring (backlog)

---

### Backlog: Word Cloud Embedding-Based Auto-Scoring & Clustering

- **Goal:** Implement word cloud question type with _no admin-set “correct” answer_. Answers are grouped via semantic similarity using sentence-transformers (MiniLM or similar). Participants receive scores proportional to the size of their answer’s semantic cluster.
- **Algorithm:** 
  - Collect all participant responses.
  - Embed using sentence-transformers.
  - Group by cosine similarity threshold or clustering (e.g., DBSCAN or flat threshold).
  - Score = 30 × (cluster size ratio).
  - Cluster representatives are displayed in a word cloud on the admin screen (popular answers shown larger).
- **Frontend:** Admin screen displays live word cloud; participant screen provides feedback on their cluster size.
- **No correct answer required in question library for this type.**
- **Library:** Use sentence-transformers for fast, local embedding/similarity.
## Key Decisions Made
- **Time-Based Scoring**: Correct answers = seconds remaining (0-30 points), incorrect = 0
- **WebSocket Architecture**: Full real-time bidirectional communication with connection management
- **Database Design**: SQLAlchemy ORM with score field and automatic cleanup
- **Load Testing Framework**: Comprehensive 150-user testing with Locust and custom monitoring
- **Admin Interface**: 3-column layout with Current Question | Live Answers | Leaderboard
- **UI/UX Design**: Christmas-themed interface with professional table styling
- **Participant Experience**: Current + cumulative score display in real-time feedback
- **Error Handling**: Debug logging and graceful failure recovery throughout the system
- **Scalability**: Optimized for 150 concurrent users with performance monitoring

## Recently Completed (Major Updates)
- ✅ **Time-Based Scoring System**: Implemented seconds-remaining scoring with cumulative tracking
- ✅ **Enhanced Participant Experience**: Current + total score display, improved feedback
- ✅ **Admin Interface Refactor**: 3-column layout, simplified dashboard, styled tables
- ✅ **Live Leaderboard**: Real-time cumulative scores with professional table design
- ✅ **Simplified Answers Table**: Streamlined to essential columns with ✓/✗ indicators
- ✅ **Fixed Quiz Start UX**: Proper "waiting for first question" message for participants
- ✅ **Real-time Updates**: Immediate leaderboard and score updates throughout quiz
- ✅ **Complete Question Management System**: Add, edit, delete questions with category organization
- ✅ **Category Analytics**: Visual breakdown showing question counts by category
- ✅ **Comprehensive Load Testing**: 150-user performance validation with detailed reporting
- ✅ **Debug Infrastructure**: Extensive logging for troubleshooting WebSocket issues
- ✅ **Documentation Overhaul**: Updated README, project brief, and memory bank

## Current Refactoring Work (Question Types Overhaul)
### New Question Type Specifications (Strict Type Convention - No Aliasing)
- **Each question type uses the literal DB value everywhere—no mappings/normalizations in backend or frontend.**

1. **fill_in_the_blank**
   - Question shown as entered
   - Multiple attempts allowed
   - Score = time remaining when correct
   - Input: voice or text
   - Display: answer table line

2. **multiple_choice**
   - Only one correct: first selection submits answer and disables choices, no green or highlight on selection
   - Score = time remaining when correct
   - Input: checkbox selection (only one)
   - Display: answer table line

3. **wheel_of_fortune**
   - Category shown, blank tiles revealed every 2 seconds
   - Multiple guesses allowed until correct
   - Score = time remaining when correct word guessed
   - Input: voice or text
   - Display: answer table line

4. **word_cloud**
   - Only question/prompt shown (no answer in database)
   - All participants answer via voice/text
   - Tally similar answers as word cloud on admin screen
   - Score = 30 × (ratio of participants with similar answer)
   - Display: word cloud visualization + answer table

5. **pictionary**
   - Admin draws based on hidden prompt
   - Drawing canvas is always shown and cleared for each new question, hidden for non-pictionary
   - Participants guess via voice/text, multiple attempts allowed
   - If answer close enough, score = time remaining
   - Custom similarity using embeddings and cosine distance
   - Display: drawing canvas + answer table

### Critical Issues Identified
- **Admin Interface Incompatibility**: Current static form doesn't support different question type requirements
- **Anti-Cheating Vulnerability**: Answers shown in real-time on admin screen (visible via Zoom)
- **Missing Database Fields**: Need `hidden_prompt` for pictionary
- **Similarity Algorithms**: Need embedding-based scoring for pictionary and word cloud grouping

## Open Questions
- Optimal embedding model for pictionary similarity scoring
- Word cloud similarity clustering algorithm thresholds
- Question sequencing algorithms for engagement
- Integration with external meeting platforms
- Mobile device optimization for smaller screens

## Next Steps (Refactoring Implementation)
1. **Database Schema Updates**: Add hidden_prompt field, update question type names
2. **Admin Interface Overhaul**: Dynamic forms for different question types
3. **Anti-Cheating Logic**: Hide answers during questions, show only after reveal
4. **Similarity Algorithms**: Implement embedding-based scoring for pictionary and word cloud
5. **Frontend Updates**: Add drawing canvas display and word cloud visualization
6. **Testing & Validation**: Comprehensive testing of new features
7. **Production Deployment**: Deploy updated system with monitoring

## Risks and Mitigations
- **Performance at Scale**: Comprehensive load testing completed with monitoring in place
- **Browser Compatibility**: Tested across modern browsers with WebSocket and voice support
- **Network Reliability**: WebSocket reconnection logic with graceful degradation
- **Data Persistence**: SQLite for development, PostgreSQL migration path established
- **Security**: Password-based admin access DISABLED for development - re-enable before production deployment
- **Refactoring Complexity**: Large-scale changes to question types - implementing incrementally with comprehensive testing
- **Similarity Algorithm Accuracy**: New embedding-based scoring may need tuning - starting with basic implementations and iterating
- **Admin UX Changes**: Dynamic forms may confuse users - providing clear visual cues and validation

## Security Tasks (Pre-Production)
- **CRITICAL**: Re-enable admin password protection once development is complete
- **IMPROVE**: Replace hardcoded password with proper authentication (OAuth/token-based)
- **TEST**: Verify authentication works across different browsers and sessions
