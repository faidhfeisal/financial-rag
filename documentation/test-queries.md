# Test Queries for RAG System Evaluation

## 1. Basic Information Retrieval

### ISO 27001 Queries
```plaintext
- What are the key requirements for access control in ISO 27001?
- Explain the documentation requirements for ISO 27001 implementation.
- What are the management responsibilities according to ISO 27001?
```
Expected: Should retrieve specific sections from 2.3 Access Control and 3.1 Documentation Requirements.

### ISO 20022 Queries
```plaintext
- List the main message types in ISO 20022.
- What is the purpose of pacs.008 message type?
- Describe the structure of ISO 20022 messages.
```
Expected: Should retrieve information from section 2.1 Payment Messages and 3.1 Message Structure.

## 2. Cross-Document Queries

```plaintext
- How do security requirements relate to financial messaging standards?
- What are the compliance requirements for handling financial transaction data?
- Explain the relationship between access control and message processing.
```
Expected: Should combine information from both documents and make relevant connections.

## 3. Complex Analytical Queries

```plaintext
- Compare the security controls required for payment processing with general ISO 27001 security guidelines.
- What are the implementation steps needed to ensure both ISO 27001 compliance and ISO 20022 message handling?
- How should an organization structure its security policy to cover both information security and financial messaging requirements?
```
Expected: Should demonstrate synthesis of information across documents.

## 4. Specific Technical Questions

### Security-Focused
```plaintext
- What are the specific password management requirements in ISO 27001?
- How should cryptographic controls be implemented according to ISO 27001?
- What are the requirements for security event logging and monitoring?
```
Expected: Should retrieve detailed technical requirements from ISO 27001 sections 2.3 and 2.4.

### Messaging-Focused
```plaintext
- What are the XML format requirements for ISO 20022 messages?
- Explain the validation requirements for payment messages.
- How should securities messages be structured according to ISO 20022?
```
Expected: Should retrieve specific technical details from sections 2.1 and 2.2.

## 5. Edge Cases and Limitations

```plaintext
- What are the requirements for quantum cryptography in ISO 27001?
- How does ISO 20022 handle blockchain-based transactions?
- What are the mobile payment message specifications in ISO 20022?
```
Expected: Should acknowledge limitations or absence of information in the documents.

## 6. Evaluation Criteria

For each query, evaluate:

1. **Accuracy**
   - Are citations correct?
   - Is information relevant?
   - Are sources properly combined?

2. **Completeness**
   - Are all relevant sections referenced?
   - Is context preserved?
   - Are important details included?

3. **Coherence**
   - Is the response well-structured?
   - Are connections logical?
   - Is the information flow clear?

4. **Source Attribution**
   - Are sources clearly cited?
   - Is confidence scoring accurate?
   - Are relevant sections highlighted?

## 7. Real-World Scenarios

```plaintext
- A bank is implementing new security controls for their payment processing system. What requirements from both ISO 27001 and ISO 20022 should they consider?
- An auditor is reviewing compliance with both standards. What documentation should be available according to both frameworks?
- A security incident has occurred in the payment system. What are the response requirements according to both standards?
```
Expected: Should provide practical, actionable responses combining both standards.

## 8. Metrics to Track

1. Response Time
   - Generation time
   - Retrieval time
   - Total latency

2. Retrieval Quality
   - Number of relevant sources
   - Citation accuracy
   - Source diversity

3. Response Quality
   - Coherence score
   - Completeness score
   - User feedback rating